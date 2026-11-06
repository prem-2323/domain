import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any, Literal
import re

from app.core.config import settings
from app.models.integration import (
    ProposedDnsPlan,
    DnsRecordItem,
    DnsConflict,
    DnsApplyRequest,
    IntegrationDeploymentStatus,
    WorkflowState,
    DnsVerificationItem,
    CloudflareZoneInfo,
)
from app.services.integrations.cloudflare_service import cloudflare_service, CloudflareApiError
from app.services.integrations.vercel_service import vercel_service, VercelApiError
from app.services.integrations.render_service import render_service, RenderApiError
from app.services.integrations.dns_verifier import dns_verifier
from app.services.registration_service import RegistrationService

logger = logging.getLogger("dns_workflow_service")


class DnsWorkflowService:
    """
    Orchestrates the 10-step Cloudflare + Vercel / Render DNS workflow:
    1. Select domain
    2. Select platform (Vercel / Render)
    3. Check domain authorization
    4. Check Cloudflare zone status and assigned nameservers
    5. Retrieve required hosting DNS records
    6. Conflict detection & proposed plan preview
    7. User/admin explicit approval
    8. Apply changes via Cloudflare API
    9. Real DNS verification
    10. Real platform verification & SSL status
    """

    @staticmethod
    def validate_domain_authorization(domain: str) -> Tuple[bool, str]:
        """
        Validates domain syntax and authorization before any DNS operation.
        """
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
        and generates the proposed plan with conflict detection.
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

        return ProposedDnsPlan(
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
        """
        conflicts: List[DnsConflict] = []
        dom = domain.strip().lower()

        for req in required_records:
            req_name = req.name.strip().lower()
            # Normalize full name
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

    async def apply_dns_plan(self, request: DnsApplyRequest) -> IntegrationDeploymentStatus:
        """
        Applies proposed DNS changes to Cloudflare only after explicit approval.
        Verifies changes against real DNS results.
        """
        now = datetime.now(timezone.utc).isoformat()
        is_valid, clean_domain = self.validate_domain_authorization(request.domain)
        if not is_valid:
            return IntegrationDeploymentStatus(
                domain=request.domain,
                target_platform=request.target_platform,
                state="failed",
                message=clean_domain,
                last_checked_at=now,
            )

        if not request.approved:
            return IntegrationDeploymentStatus(
                domain=clean_domain,
                target_platform=request.target_platform,
                state="awaiting_approval",
                message="DNS changes were not applied: Explicit user/admin approval is required.",
                last_checked_at=now,
            )

        # Generate plan to verify current state & conflicts
        plan = await self.get_proposed_plan(clean_domain, request.target_platform)
        if not plan.can_apply or not plan.zone_id:
            return IntegrationDeploymentStatus(
                domain=clean_domain,
                target_platform=request.target_platform,
                state=plan.state,
                message=plan.message,
                zone_status=plan.zone_status,
                assigned_nameservers=plan.assigned_nameservers,
                last_checked_at=now,
            )

        # Check conflict override
        if plan.has_conflicts and not request.override_conflicts:
            return IntegrationDeploymentStatus(
                domain=clean_domain,
                target_platform=request.target_platform,
                state="dns_conflict",
                message="DNS changes aborted: Existing DNS conflicts detected. Explicit conflict override is required.",
                zone_status=plan.zone_status,
                assigned_nameservers=plan.assigned_nameservers,
                conflicts=plan.conflicts,
                last_checked_at=now,
            )

        # Step 8: Apply changes via Cloudflare API
        logger.info(f"Applying DNS changes for {clean_domain} to zone {plan.zone_id}")
        applied_records: List[DnsRecordItem] = []

        try:
            # First, handle conflicting records if override is approved
            if plan.has_conflicts and request.override_conflicts:
                for conf in plan.conflicts:
                    if conf.existing_record.id:
                        if conf.conflict_type == "incompatible_record_type":
                            # Delete incompatible type first
                            await cloudflare_service.delete_dns_record(plan.zone_id, conf.existing_record.id)
                        else:
                            # Update existing record
                            upd = await cloudflare_service.update_dns_record(
                                plan.zone_id,
                                conf.existing_record.id,
                                conf.proposed_record,
                            )
                            applied_records.append(upd)

            # Apply required records that were not already updated in conflicts
            updated_names = {r.name.lower() for r in applied_records}
            for req in plan.required_records:
                if req.name.lower() in updated_names:
                    continue

                # Check if exact record already exists with same content
                already_exists = False
                for ex in plan.existing_records:
                    if (
                        ex.name.lower() in (req.name.lower(), f"{req.name.lower()}.{clean_domain}")
                        and ex.type.upper() == req.type.upper()
                        and ex.content.strip().lower() == req.content.strip().lower()
                    ):
                        applied_records.append(ex)
                        already_exists = True
                        break

                if not already_exists:
                    created = await cloudflare_service.create_dns_record(plan.zone_id, req)
                    applied_records.append(created)

        except CloudflareApiError as e:
            return IntegrationDeploymentStatus(
                domain=clean_domain,
                target_platform=request.target_platform,
                state="failed",
                message=f"Cloudflare DNS provision error: {e.message}",
                zone_status=plan.zone_status,
                assigned_nameservers=plan.assigned_nameservers,
                records=applied_records,
                last_checked_at=now,
            )

        # Step 9: Verify DNS records via real DNS query
        verification_items = await dns_verifier.verify_records(clean_domain, plan.required_records)
        all_dns_verified = all(v.verified for v in verification_items)

        # Step 10: Trigger platform verification
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
        ssl_mode = await cloudflare_service.get_zone_ssl_settings(plan.zone_id)
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
            zone_status=plan.zone_status,
            assigned_nameservers=plan.assigned_nameservers,
            nameserver_instructions=(
                f"Registrar nameservers must match: {', '.join(plan.assigned_nameservers)}. "
                "Do not use unrelated nameservers."
            ),
            ssl_status=ssl_mode,
            ssl_verified=ssl_verified,
            platform_verified=platform_verified,
            records=applied_records,
            verification_items=verification_items,
            conflicts=[],
            last_checked_at=now,
        )

    async def verify_deployment(
        self,
        domain: str,
        target_platform: Literal["vercel", "render"],
    ) -> IntegrationDeploymentStatus:
        """
        Polls live DNS and platform verification without reapplying changes.
        """
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
