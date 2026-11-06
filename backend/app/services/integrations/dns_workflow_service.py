import logging
import json
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any, Literal
import re
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.dns_audit import DnsAuditManager
from app.models.integration import (
    ProposedDnsPlan,
    DnsRecordItem,
    DnsConflict,
    DnsApplyRequest,
    IntegrationDeploymentStatus,
    WorkflowState,
    CloudflareZoneInfo,
)
from app.services.integrations.cloudflare_service import (
    cloudflare_service,
    is_protected_record,
    CloudflareApiError,
)
from app.services.integrations.vercel_service import vercel_service, VercelApiError
from app.services.integrations.render_service import render_service, RenderApiError
from app.services.integrations.dns_verifier import dns_verifier
from app.services.registration_service import RegistrationService

logger = logging.getLogger("dns_workflow_service")


def compute_canonical_records_string(records: List[DnsRecordItem]) -> str:
    """Computes a deterministic canonical string for a list of DNS records."""
    parts = []
    for r in sorted(records, key=lambda x: (x.name.lower(), x.type.upper(), x.content.strip())):
        parts.append(f"{r.type.upper()}:{r.name.lower()}:{r.content.strip()}:{1 if r.proxied else 0}")
    return ";".join(parts)


def compute_records_drift_hash(records: List[DnsRecordItem]) -> str:
    """Computes a SHA-256 hash of existing DNS records to detect drift prior to apply."""
    parts = []
    for r in sorted(records, key=lambda x: (x.id or "", x.name.lower(), x.type.upper(), x.content.strip())):
        parts.append(f"{r.id or ''}:{r.type.upper()}:{r.name.lower()}:{r.content.strip()}")
    raw = ";".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_plan_signature(
    plan_id: str,
    plan_version: int,
    domain: str,
    target_platform: str,
    zone_id: str,
    required_records: List[DnsRecordItem],
    expires_at: str,
    existing_records_hash: str,
) -> str:
    """Generates an HMAC-SHA256 signature cryptographically binding all DNS plan parameters."""
    secret = settings.SECRET_KEY or "fallback-test-secret-key-123"
    canonical = compute_canonical_records_string(required_records)
    payload = f"{plan_id}:{plan_version}:{domain.lower()}:{target_platform.lower()}:{zone_id}:{canonical}:{expires_at}:{existing_records_hash}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


class ServerDnsPlanStore:
    """Persistent SQLite store for server-side generated DNS plans."""

    @classmethod
    def _init_table(cls) -> None:
        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS server_dns_plans (
                    plan_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    target_platform TEXT NOT NULL,
                    zone_id TEXT NOT NULL,
                    plan_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    plan_signature TEXT NOT NULL,
                    existing_records_hash TEXT NOT NULL,
                    required_records_json TEXT NOT NULL,
                    conflicts_json TEXT NOT NULL,
                    has_conflicts INTEGER NOT NULL DEFAULT 0,
                    applied INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_domain ON server_dns_plans(domain)")
            conn.commit()

    @classmethod
    def save_plan(
        cls,
        plan_id: str,
        domain: str,
        target_platform: str,
        zone_id: str,
        plan_version: int,
        created_at: str,
        expires_at: str,
        plan_signature: str,
        existing_records_hash: str,
        required_records: List[DnsRecordItem],
        conflicts: List[DnsConflict],
        has_conflicts: bool,
    ) -> None:
        cls._init_table()
        req_json = json.dumps([r.model_dump() for r in required_records])
        conf_json = json.dumps([c.model_dump() for c in conflicts])
        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO server_dns_plans (
                    plan_id, domain, target_platform, zone_id, plan_version,
                    created_at, expires_at, plan_signature, existing_records_hash,
                    required_records_json, conflicts_json, has_conflicts, applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    plan_id,
                    domain.lower(),
                    target_platform.lower(),
                    zone_id,
                    plan_version,
                    created_at,
                    expires_at,
                    plan_signature,
                    existing_records_hash,
                    req_json,
                    conf_json,
                    1 if has_conflicts else 0,
                ),
            )
            conn.commit()

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[Dict[str, Any]]:
        cls._init_table()
        with RegistrationService._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM server_dns_plans WHERE plan_id = ?",
                (plan_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @classmethod
    def mark_applied(cls, plan_id: str) -> None:
        cls._init_table()
        with RegistrationService._get_connection() as conn:
            conn.execute(
                "UPDATE server_dns_plans SET applied = 1 WHERE plan_id = ?",
                (plan_id,),
            )
            conn.commit()


ServerDnsPlanStore._init_table()


class DnsWorkflowService:
    """
    Orchestrates the secure 10-step Cloudflare + Vercel / Render DNS workflow:
    1. Select domain
    2. Select platform (Vercel / Render)
    3. Check domain authorization
    4. Check Cloudflare zone status and assigned nameservers
    5. Retrieve required hosting DNS records
    6. Conflict detection & server-side proposed plan cryptographic preview
    7. Authenticated administrator explicit approval
    8. Apply changes safely via Cloudflare API
    9. Real DNS verification
    10. Real platform verification & SSL status
    """

    @staticmethod
    def validate_domain_authorization(domain: str) -> Tuple[bool, str]:
        """Validates domain syntax and authorization before any DNS operation."""
        dom = domain.strip().lower().rstrip(".")
        if not dom or len(dom) < 3 or len(dom) > 253:
            return False, f"Invalid domain name length: '{domain}'"

        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", dom):
            return False, f"Invalid domain format: '{domain}'"

        return True, dom

    async def get_proposed_plan(
        self,
        domain: str,
        target_platform: Literal["vercel", "render"],
    ) -> ProposedDnsPlan:
        """
        Inspects zone and hosting requirements, compares with existing DNS records,
        and generates a signed server-side proposed plan with conflict detection.
        """
        is_valid, clean_domain = self.validate_domain_authorization(domain)
        if not is_valid:
            return ProposedDnsPlan(
                domain=domain,
                target_platform=target_platform,
                state="failed",
                message=clean_domain,
                can_apply=False,
                requires_approval=True,
            )

        # 1. Check Cloudflare Credentials
        if not cloudflare_service.is_configured:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                state="credentials_missing",
                message="Cloudflare API token is not configured on the backend server.",
                can_apply=False,
                requires_approval=True,
            )

        # 2. Check Hosting Platform Credentials
        if target_platform == "vercel" and not vercel_service.is_configured:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                state="credentials_missing",
                message="Vercel API token or Project ID is not configured on the backend server.",
                can_apply=False,
                requires_approval=True,
            )
        elif target_platform == "render" and not render_service.is_configured:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                state="credentials_missing",
                message="Render API key or Service ID is not configured on the backend server.",
                can_apply=False,
                requires_approval=True,
            )

        # 3. Look up Cloudflare Zone
        try:
            zone = await cloudflare_service.get_zone_for_domain(clean_domain)
        except CloudflareApiError as e:
            if e.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "ZONE_ACCESS_DENIED", "message": e.message},
                )
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                state="failed",
                message=f"Cloudflare zone lookup error: {e.message}",
                can_apply=False,
                requires_approval=True,
            )

        if not zone:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                state="failed",
                message=f"No Cloudflare zone found for '{clean_domain}'. Ensure the zone exists in your Cloudflare account.",
                can_apply=False,
                requires_approval=True,
            )

        assigned_ns = zone.name_servers or []
        is_zone_active = zone.status.lower() == "active"

        # Check zone status
        if not is_zone_active:
            state: WorkflowState = "awaiting_nameserver_update" if zone.status.lower() == "pending" else "zone_pending_activation"
            ns_str = ", ".join(assigned_ns) if assigned_ns else "assigned Cloudflare nameservers"
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                zone_id=zone.zone_id,
                zone_name=zone.name,
                zone_status=zone.status,
                assigned_nameservers=assigned_ns,
                is_zone_active=False,
                state=state,
                message=(
                    f"Cloudflare reports zone status '{zone.status}'. Nameservers ({ns_str}) "
                    "are assigned specifically for this zone and must be updated at your registrar. "
                    "Cloudflare zone activation is required before DNS routing takes effect."
                ),
                can_apply=False,
                requires_approval=True,
            )

        # 4. Retrieve Required Hosting Records
        try:
            if target_platform == "vercel":
                required_records = await vercel_service.get_required_dns_records(clean_domain)
            else:
                required_records = await render_service.get_required_dns_records(clean_domain)
        except (VercelApiError, RenderApiError) as e:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                zone_id=zone.zone_id,
                zone_name=zone.name,
                zone_status=zone.status,
                assigned_nameservers=assigned_ns,
                is_zone_active=True,
                state="failed",
                message=f"Failed to fetch required DNS records from {target_platform.capitalize()}: {e.message}",
                can_apply=False,
                requires_approval=True,
            )

        # 5. Fetch Existing Cloudflare DNS Records
        try:
            existing_records = await cloudflare_service.list_dns_records(zone.zone_id)
        except CloudflareApiError as e:
            return ProposedDnsPlan(
                domain=clean_domain,
                target_platform=target_platform,
                zone_id=zone.zone_id,
                zone_name=zone.name,
                zone_status=zone.status,
                assigned_nameservers=assigned_ns,
                is_zone_active=True,
                required_records=required_records,
                state="failed",
                message=f"Failed to list existing Cloudflare DNS records: {e.message}",
                can_apply=False,
                requires_approval=True,
            )

        # 6. Detect DNS Conflicts
        conflicts = self.detect_conflicts(clean_domain, required_records, existing_records)
        has_conflicts = len(conflicts) > 0

        state = "dns_conflict" if has_conflicts else "awaiting_approval"
        msg = (
            f"Detected {len(conflicts)} conflicting DNS record(s). Explicit approval required to overwrite."
            if has_conflicts
            else f"Proposed {len(required_records)} record(s) ready for review. Awaiting approval to apply."
        )

        # 7. Cryptographically bind server-side plan
        plan_id = f"plan_{secrets.token_hex(16)}"
        plan_version = 1
        now_dt = datetime.now(timezone.utc)
        created_at = now_dt.isoformat()
        expires_at = (now_dt + timedelta(minutes=15)).isoformat()
        existing_records_hash = compute_records_drift_hash(existing_records)
        plan_signature = generate_plan_signature(
            plan_id=plan_id,
            plan_version=plan_version,
            domain=clean_domain,
            target_platform=target_platform,
            zone_id=zone.zone_id,
            required_records=required_records,
            expires_at=expires_at,
            existing_records_hash=existing_records_hash,
        )

        # Persist server-side plan
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform=target_platform,
            zone_id=zone.zone_id,
            plan_version=plan_version,
            created_at=created_at,
            expires_at=expires_at,
            plan_signature=plan_signature,
            existing_records_hash=existing_records_hash,
            required_records=required_records,
            conflicts=conflicts,
            has_conflicts=has_conflicts,
        )

        return ProposedDnsPlan(
            plan_id=plan_id,
            plan_version=plan_version,
            created_at=created_at,
            expires_at=expires_at,
            plan_signature=plan_signature,
            existing_records_hash=existing_records_hash,
            domain=clean_domain,
            target_platform=target_platform,
            zone_id=zone.zone_id,
            zone_name=zone.name,
            zone_status=zone.status,
            assigned_nameservers=assigned_ns,
            is_zone_active=True,
            required_records=required_records,
            existing_records=existing_records,
            conflicts=conflicts,
            has_conflicts=has_conflicts,
            state=state,
            message=msg,
            can_apply=True,
            requires_approval=True,
        )

    def detect_conflicts(
        self,
        domain: str,
        required_records: List[DnsRecordItem],
        existing_records: List[DnsRecordItem],
    ) -> List[DnsConflict]:
        """
        Compares required records against existing records in Cloudflare.
        Identifies any record that would overwrite an existing target or violate CNAME exclusivity.
        Preserves protected records (MX, SPF, DKIM) from being overwritten.
        """
        conflicts: List[DnsConflict] = []
        dom = domain.strip().lower()

        for req in required_records:
            req_name = req.name.strip().lower()
            if req_name in ("@", "", dom):
                req_fqdn = dom
            elif req_name.endswith(f".{dom}"):
                req_fqdn = req_name
            else:
                req_fqdn = f"{req_name}.{dom}"

            for ex in existing_records:
                ex_name = ex.name.strip().lower()
                if ex_name in ("@", "", dom):
                    ex_fqdn = dom
                elif ex_name.endswith(f".{dom}"):
                    ex_fqdn = ex_name
                else:
                    ex_fqdn = f"{ex_name}.{dom}"

                if req_fqdn == ex_fqdn:
                    # Same name: check if content or type differs
                    if ex.type.upper() == req.type.upper():
                        if ex.content.strip().lower() != req.content.strip().lower():
                            conflicts.append(
                                DnsConflict(
                                    existing_record=ex,
                                    proposed_record=req,
                                    conflict_type="existing_record_differs",
                                    message=(
                                        f"Existing {ex.type} record for '{ex_fqdn}' points to '{ex.content}', "
                                        f"which differs from proposed '{req.content}'."
                                    ),
                                    requires_override=True,
                                )
                            )
                    else:
                        # Incompatible record type on the same name (e.g. CNAME vs A)
                        conflicts.append(
                            DnsConflict(
                                existing_record=ex,
                                proposed_record=req,
                                conflict_type="incompatible_record_type",
                                message=(
                                    f"Existing {ex.type} record on '{ex_fqdn}' conflicts with "
                                    f"proposed {req.type} record (RFC 1912 exclusivity)."
                                ),
                                requires_override=True,
                            )
                        )

        return conflicts

    async def apply_dns_plan(
        self,
        request: DnsApplyRequest,
        admin_username: str = "admin",
    ) -> IntegrationDeploymentStatus:
        """
        Applies proposed DNS changes to Cloudflare only after authenticated administrator approval.
        Enforces plan signature integrity, plan expiration check, drift detection, and conflict override.
        Preserves protected records and records an SQLite audit trail for every change.
        """
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()

        # Domain validation
        is_valid, clean_domain = self.validate_domain_authorization(request.domain)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_DOMAIN", "message": clean_domain},
            )

        # 1. Require explicit administrator approval
        if not request.approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "APPROVAL_REQUIRED",
                    "message": "Explicit administrator approval is required to create or modify DNS records.",
                },
            )

        # 2. Check Plan Expiration
        try:
            expires_dt = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
            if expires_dt < now_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PLAN_EXPIRED",
                        "message": "The DNS plan has expired. Please inspect and approve a new plan.",
                    },
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PLAN_EXPIRED", "message": "Invalid or expired plan timestamp format."},
            )

        # 3. Retrieve Server-Side Plan
        stored_plan = ServerDnsPlanStore.get_plan(request.plan_id)
        if not stored_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PLAN_TAMPERED", "message": "DNS plan ID is unrecognized, expired, or modified."},
            )

        if stored_plan["applied"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PLAN_ALREADY_APPLIED", "message": "This DNS plan has already been executed."},
            )
        if (
            stored_plan["domain"] != clean_domain
            or stored_plan["target_platform"] != request.target_platform.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PLAN_TAMPERED", "message": "Plan parameters do not match server record."},
            )
        if not secrets.compare_digest(request.plan_signature, stored_plan["plan_signature"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PLAN_TAMPERED", "message": "DNS plan cryptographic signature mismatch."},
            )
        zone_id = stored_plan["zone_id"]
        required_records = [DnsRecordItem(**r) for r in json.loads(stored_plan["required_records_json"])]
        conflicts = [DnsConflict(**c) for c in json.loads(stored_plan["conflicts_json"])]
        has_conflicts = bool(stored_plan["has_conflicts"])
        expected_drift_hash = stored_plan["existing_records_hash"]

        # 4. Immediate Pre-Apply Re-Check of Cloudflare DNS Records (DNS Drift Detection)
        try:
            current_existing_records = await cloudflare_service.list_dns_records(zone_id)
        except CloudflareApiError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={"error": "CLOUDFLARE_LOOKUP_FAILED", "message": e.message},
            )

        current_drift_hash = compute_records_drift_hash(current_existing_records)
        if current_drift_hash != expected_drift_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "DNS_DRIFT_DETECTED",
                    "message": "Existing DNS records in Cloudflare have changed since plan creation. Please review the updated plan.",
                },
            )

        # 5. Check Conflict Overrides Requirement
        if has_conflicts and not request.override_conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "CONFLICT_OVERRIDE_REQUIRED",
                    "message": "Existing DNS conflicts detected. A separate explicit conflict override approval is required.",
                },
            )

        # 6. Verify Protected Records Integrity (MX, SPF, DKIM, CAA, etc.)
        for conf in conflicts:
            if is_protected_record(conf.existing_record):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PROTECTED_RECORD_CONFLICT",
                        "message": (
                            f"Cannot overwrite or modify protected record '{conf.existing_record.type} "
                            f"{conf.existing_record.name}'. Email/security records are strictly preserved."
                        ),
                    },
                )

        # 7. Apply Changes Safely to Cloudflare
        logger.info(f"Applying approved DNS changes for {clean_domain} in zone {zone_id} by admin '{admin_username}'")
        applied_records: List[DnsRecordItem] = []

        try:
            # Handle conflicting records if override is approved
            if has_conflicts and request.override_conflicts:
                for conf in conflicts:
                    if conf.existing_record.id:
                        if conf.conflict_type == "incompatible_record_type":
                            # Delete incompatible record type to satisfy RFC 1912 CNAME exclusivity
                            await cloudflare_service.delete_dns_record(
                                zone_id,
                                conf.existing_record.id,
                                record=conf.existing_record,
                            )
                            DnsAuditManager.record_change(
                                admin_username=admin_username,
                                action="DELETE_CONFLICTING_RECORD",
                                domain=clean_domain,
                                zone_id=zone_id,
                                record_type=conf.existing_record.type,
                                record_name=conf.existing_record.name,
                                old_content=conf.existing_record.content,
                                details="Deleted incompatible record type for RFC 1912 CNAME exclusivity",
                            )
                        else:
                            # Update existing record in place
                            upd = await cloudflare_service.update_dns_record(
                                zone_id,
                                conf.existing_record.id,
                                conf.proposed_record,
                            )
                            applied_records.append(upd)
                            DnsAuditManager.record_change(
                                admin_username=admin_username,
                                action="UPDATE_RECORD",
                                domain=clean_domain,
                                zone_id=zone_id,
                                record_type=upd.type,
                                record_name=upd.name,
                                old_content=conf.existing_record.content,
                                new_content=upd.content,
                                ttl=upd.ttl,
                                proxied=upd.proxied,
                                details="Updated existing conflicting record",
                            )

            # Apply required records that were not already updated in conflicts
            updated_names = {r.name.lower() for r in applied_records}
            for req in required_records:
                if req.name.lower() in updated_names:
                    continue

                # Check if exact record already exists with same content
                already_exists = False
                for ex in current_existing_records:
                    if (
                        ex.name.lower() in (req.name.lower(), f"{req.name.lower()}.{clean_domain}")
                        and ex.type.upper() == req.type.upper()
                        and ex.content.strip().lower() == req.content.strip().lower()
                    ):
                        applied_records.append(ex)
                        already_exists = True
                        break

                if not already_exists:
                    created = await cloudflare_service.create_dns_record(zone_id, req)
                    applied_records.append(created)
                    DnsAuditManager.record_change(
                        admin_username=admin_username,
                        action="CREATE_RECORD",
                        domain=clean_domain,
                        zone_id=zone_id,
                        record_type=created.type,
                        record_name=created.name,
                        new_content=created.content,
                        ttl=created.ttl,
                        proxied=created.proxied,
                        details="Created required hosting DNS record",
                    )

            # Mark plan applied
            if stored_plan:
                ServerDnsPlanStore.mark_applied(request.plan_id)

        except CloudflareApiError as e:
            raise HTTPException(status_code=e.status_code, detail={"error": "CLOUDFLARE_ERROR", "message": e.message})

        # Step 8: Verify DNS records via authoritative DNS query
        verification_items = await dns_verifier.verify_records(clean_domain, required_records)
        all_dns_verified = all(v.verified for v in verification_items)

        # Step 9: Trigger platform verification
        platform_verified = False
        try:
            if request.target_platform == "vercel":
                ver_res = await vercel_service.verify_domain(clean_domain)
                platform_verified = bool(ver_res.get("verified", False))
            else:
                ren_res = await render_service.verify_custom_domain(clean_domain)
                status_str = ren_res.get("verificationStatus") or ren_res.get("status")
                platform_verified = str(status_str).lower() == "verified"
        except Exception as e:
            logger.warning(f"Platform verification call failed: {e}")
            platform_verified = False

        # SSL status from Cloudflare
        ssl_mode = await cloudflare_service.get_zone_ssl_settings(zone_id)
        ssl_verified = bool(all_dns_verified and platform_verified and ssl_mode in ("full", "strict"))

        if all_dns_verified and platform_verified:
            state = "connected"
            msg = f"Domain '{clean_domain}' successfully connected to {request.target_platform.capitalize()} with active DNS."
        elif all_dns_verified and not platform_verified:
            state = "provisioning"
            msg = (
                f"DNS records successfully written to Cloudflare and verified in DNS. "
                f"Awaiting final verification from {request.target_platform.capitalize()}."
            )
        else:
            state = "dns_verification_pending"
            unverified_names = [v.name for v in verification_items if not v.verified]
            msg = (
                f"Records written to Cloudflare. Live DNS propagation pending for: "
                f"{', '.join(unverified_names)}. TTL is 60s."
            )

        return IntegrationDeploymentStatus(
            domain=clean_domain,
            target_platform=request.target_platform,
            state=state,
            message=msg,
            records=applied_records,
            verification_items=verification_items,
            conflicts=[],
            ssl_status=ssl_mode,
            ssl_verified=ssl_verified,
            platform_verified=platform_verified,
            last_checked_at=now,
        )

    async def verify_deployment(
        self,
        domain: str,
        target_platform: Literal["vercel", "render"],
    ) -> IntegrationDeploymentStatus:
        """Polls live DNS and platform verification without reapplying changes."""
        now = datetime.now(timezone.utc).isoformat()
        is_valid, clean_domain = self.validate_domain_authorization(domain)
        if not is_valid:
            return IntegrationDeploymentStatus(
                domain=domain,
                target_platform=target_platform,
                state="failed",
                message=clean_domain,
                last_checked_at=now,
            )

        plan = await self.get_proposed_plan(clean_domain, target_platform)
        if plan.state != "awaiting_approval" and plan.state != "dns_conflict":
            return IntegrationDeploymentStatus(
                domain=clean_domain,
                target_platform=target_platform,
                state=plan.state,
                message=plan.message,
                zone_status=plan.zone_status,
                assigned_nameservers=plan.assigned_nameservers,
                last_checked_at=now,
            )

        # Real DNS check
        verification_items = await dns_verifier.verify_records(clean_domain, plan.required_records)
        all_dns_verified = all(v.verified for v in verification_items)

        # Platform check
        platform_verified = False
        if target_platform == "vercel" and vercel_service.is_configured:
            try:
                proj_dom = await vercel_service.get_project_domain(clean_domain)
                platform_verified = bool(proj_dom and proj_dom.get("verified"))
            except Exception:
                platform_verified = False
        elif target_platform == "render" and render_service.is_configured:
            try:
                ren_dom = await render_service.get_custom_domain(clean_domain)
                platform_verified = bool(
                    ren_dom and str(ren_dom.get("verificationStatus", "")).lower() == "verified"
                )
            except Exception:
                platform_verified = False

        ssl_mode = await cloudflare_service.get_zone_ssl_settings(plan.zone_id) if plan.zone_id else None
        ssl_verified = bool(all_dns_verified and platform_verified and ssl_mode in ("full", "strict"))

        if all_dns_verified and platform_verified:
            state: WorkflowState = "connected"
            msg = f"Domain '{clean_domain}' is fully connected to {target_platform.capitalize()}."
        elif all_dns_verified and not platform_verified:
            state = "provisioning"
            msg = f"DNS is live. Awaiting {target_platform.capitalize()} edge certificate issuance."
        elif any(v.verified for v in verification_items):
            state = "dns_verification_pending"
            msg = "Partial DNS propagation detected. Awaiting all records to verify."
        else:
            state = "not_connected"
            msg = f"DNS records for {target_platform.capitalize()} are not currently active in internet DNS."

        return IntegrationDeploymentStatus(
            domain=clean_domain,
            target_platform=target_platform,
            state=state,
            message=msg,
            zone_status=plan.zone_status,
            assigned_nameservers=plan.assigned_nameservers,
            nameserver_instructions=(
                f"Cloudflare zone assigned nameservers: {', '.join(plan.assigned_nameservers)}."
            ),
            ssl_status=ssl_mode,
            ssl_verified=ssl_verified,
            platform_verified=platform_verified,
            records=plan.required_records,
            verification_items=verification_items,
            conflicts=plan.conflicts,
            last_checked_at=now,
        )


dns_workflow_service = DnsWorkflowService()
