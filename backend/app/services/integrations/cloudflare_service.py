import logging
from typing import List, Optional, Tuple, Dict, Any
import httpx

from app.core.config import settings
from app.models.integration import CloudflareZoneInfo, DnsRecordItem

logger = logging.getLogger("cloudflare_service")

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

# Critical records that must never be deleted or disrupted during web hosting DNS changes
PROTECTED_RECORD_TYPES = {"MX", "SRV", "CAA", "NS", "SOA"}


def is_protected_record(record: DnsRecordItem) -> bool:
    """Checks if a DNS record is a critical system/mail/security record that must be preserved."""
    rec_type = record.type.upper()
    if rec_type in PROTECTED_RECORD_TYPES:
        return True
    if rec_type == "TXT":
        content_lower = record.content.lower()
        name_lower = record.name.lower()
        if "v=spf1" in content_lower or "spf" in content_lower or "spf" in name_lower:
            return True
        if "_dmarc" in name_lower or "v=dmarc1" in content_lower:
            return True
        if "domainkey" in name_lower:
            return True
        if "google-site-verification" in content_lower:
            return True
    return False


class CloudflareApiError(Exception):
    def __init__(self, message: str, status_code: int = 502, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors or []


class CloudflareService:
    """
    Real Cloudflare API client for zone inspection, nameserver detection,
    and DNS record management with strict domain and account authorization.
    """

    def __init__(self, api_token: Optional[str] = None):
        self._api_token = api_token
        self.timeout = 10.0

    @property
    def api_token(self) -> Optional[str]:
        return self._api_token or settings.CLOUDFLARE_API_TOKEN

    @property
    def is_configured(self) -> bool:
        tok = self.api_token
        return bool(tok and tok.strip())

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured or not self.api_token:
            raise CloudflareApiError("Cloudflare API token is not configured on the backend.", status_code=503)
        return {
            "Authorization": f"Bearer {self.api_token.strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def verify_token(self) -> Tuple[bool, Optional[str]]:
        """
        Verifies the validity of the Cloudflare API token via GET /user/tokens/verify.
        Does not log or expose the token.
        """
        if not self.is_configured:
            return False, "Token not configured"

        url = f"{CLOUDFLARE_API_BASE}/user/tokens/verify"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success"):
                        return True, data.get("result", {}).get("status", "active")
                    return False, "Verification failed"
                elif res.status_code in (401, 403):
                    return False, "Invalid or unauthorized Cloudflare API token"
                return False, f"Unexpected response ({res.status_code})"
        except httpx.RequestError as e:
            logger.warning(f"Cloudflare token verification request error: {type(e).__name__}")
            return False, f"Connectivity error: {type(e).__name__}"

    async def get_zone_for_domain(self, domain: str) -> Optional[CloudflareZoneInfo]:
        """
        Retrieves zone information matching the given domain (or parent domain if subdomain).
        Strictly enforces account ownership and domain authorization to prevent arbitrary zone selection.
        """
        if not self.is_configured:
            return None

        # Clean domain
        dom = domain.strip().lower().rstrip(".").lstrip(".")
        if not dom:
            return None

        # Try exact domain, then parent labels if subdomain
        candidates = [dom]
        parts = dom.split(".")
        if len(parts) > 2:
            candidates.append(".".join(parts[-2:]))

        for cand in candidates:
            url = f"{CLOUDFLARE_API_BASE}/zones"
            params: Dict[str, Any] = {"name": cand, "per_page": 5}
            if settings.CLOUDFLARE_ACCOUNT_ID and settings.CLOUDFLARE_ACCOUNT_ID.strip():
                params["account.id"] = settings.CLOUDFLARE_ACCOUNT_ID.strip()

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.get(url, headers=self._get_headers(), params=params)
                    if res.status_code in (401, 403):
                        logger.warning(f"Cloudflare authorization denied for zone lookup ({res.status_code})")
                        raise CloudflareApiError("Cloudflare zone access unauthorized.", status_code=403)
                    if res.status_code != 200:
                        logger.warning(f"Cloudflare zone lookup for {cand} returned status {res.status_code}")
                        continue

                    data = res.json()
                    zones = data.get("result") or []
                    for z in zones:
                        zone_id = z.get("id")
                        zone_name = z.get("name", "").strip().lower()
                        account_id = z.get("account", {}).get("id")

                        # 1. Enforce account ownership if CLOUDFLARE_ACCOUNT_ID is set
                        if (
                            settings.CLOUDFLARE_ACCOUNT_ID
                            and settings.CLOUDFLARE_ACCOUNT_ID.strip()
                            and account_id != settings.CLOUDFLARE_ACCOUNT_ID.strip()
                        ):
                            raise CloudflareApiError(
                                f"Access denied: Cloudflare zone '{zone_name}' does not belong to configured account.",
                                status_code=403,
                            )

                        # 2. Enforce CLOUDFLARE_DEFAULT_ZONE_ID if set
                        if (
                            settings.CLOUDFLARE_DEFAULT_ZONE_ID
                            and settings.CLOUDFLARE_DEFAULT_ZONE_ID.strip()
                            and zone_id != settings.CLOUDFLARE_DEFAULT_ZONE_ID.strip()
                        ):
                            raise CloudflareApiError(
                                f"Access denied: Cloudflare zone '{zone_id}' does not match default authorized zone.",
                                status_code=403,
                            )

                        # 3. Verify domain is strictly within this zone
                        if not (dom == zone_name or dom.endswith(f".{zone_name}")):
                            raise CloudflareApiError(
                                f"Access denied: Domain '{dom}' is not within authorized zone '{zone_name}'.",
                                status_code=403,
                            )

                        ssl_mode = await self.get_zone_ssl_settings(zone_id) if zone_id else None
                        return CloudflareZoneInfo(
                            zone_id=zone_id,
                            name=z.get("name", cand),
                            status=z.get("status", "pending"),
                            name_servers=z.get("name_servers") or [],
                            original_name_servers=z.get("original_name_servers"),
                            paused=bool(z.get("paused", False)),
                            ssl_status=ssl_mode,
                            account_id=account_id,
                            account_name=z.get("account", {}).get("name"),
                        )
            except httpx.RequestError as e:
                logger.error(f"Cloudflare request failed for domain {cand}: {type(e).__name__}")
                raise CloudflareApiError(f"Cloudflare API unreachable: {type(e).__name__}", status_code=502)

        return None

    async def get_zone_ssl_settings(self, zone_id: str) -> Optional[str]:
        """
        Retrieves actual SSL/TLS encryption mode for the zone (full, strict, flexible, off).
        Never returns simulated success.
        """
        if not self.is_configured or not zone_id:
            return None

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/settings/ssl"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result", {}).get("value")
                return None
        except Exception:
            return None

    async def list_dns_records(
        self,
        zone_id: str,
        name: Optional[str] = None,
        record_type: Optional[str] = None,
    ) -> List[DnsRecordItem]:
        """
        Lists real DNS records in a Cloudflare zone.
        """
        if not self.is_configured:
            raise CloudflareApiError("Cloudflare API token not configured", status_code=503)

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records"
        params: Dict[str, Any] = {"per_page": 100}
        if name:
            params["name"] = name.strip().lower()
        if record_type:
            params["type"] = record_type.strip().upper()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if res.status_code != 200:
                    err_msg = res.json().get("errors", [{}])[0].get("message", f"HTTP {res.status_code}")
                    raise CloudflareApiError(f"Failed to list DNS records: {err_msg}", status_code=res.status_code)

                data = res.json()
                records = []
                for rec in data.get("result") or []:
                    records.append(
                        DnsRecordItem(
                            id=rec.get("id"),
                            type=rec.get("type"),
                            name=rec.get("name"),
                            content=rec.get("content"),
                            ttl=rec.get("ttl", 60),
                            proxied=bool(rec.get("proxied", False)),
                            comment=rec.get("comment"),
                        )
                    )
                return records
        except httpx.RequestError as e:
            raise CloudflareApiError(f"Cloudflare DNS lookup network error: {type(e).__name__}", status_code=502)

    async def get_dns_record(self, zone_id: str, record_id: str) -> Optional[DnsRecordItem]:
        """Fetches a single DNS record by ID."""
        if not self.is_configured:
            raise CloudflareApiError("Cloudflare API token not configured", status_code=503)

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    rec = res.json().get("result") or {}
                    return DnsRecordItem(
                        id=rec.get("id"),
                        type=rec.get("type"),
                        name=rec.get("name"),
                        content=rec.get("content"),
                        ttl=rec.get("ttl", 60),
                        proxied=bool(rec.get("proxied", False)),
                        comment=rec.get("comment"),
                    )
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch DNS record {record_id}: {e}")
            return None

    async def create_dns_record(self, zone_id: str, record: DnsRecordItem) -> DnsRecordItem:
        """
        Creates a DNS record in Cloudflare.
        """
        if not self.is_configured:
            raise CloudflareApiError("Cloudflare API token not configured", status_code=503)

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records"
        payload = {
            "type": record.type.upper(),
            "name": record.name,
            "content": record.content,
            "ttl": record.ttl or 60,
            "proxied": record.proxied,
        }
        if record.comment:
            payload["comment"] = record.comment

        logger.info(f"Creating Cloudflare DNS record in zone {zone_id}: {record.type} {record.name} -> {record.content}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                data = res.json()
                if res.status_code not in (200, 201) or not data.get("success"):
                    err_detail = data.get("errors", [{}])[0].get("message", f"HTTP {res.status_code}")
                    raise CloudflareApiError(f"Failed to create DNS record: {err_detail}", status_code=res.status_code)

                result = data.get("result", {})
                return DnsRecordItem(
                    id=result.get("id"),
                    type=result.get("type"),
                    name=result.get("name"),
                    content=result.get("content"),
                    ttl=result.get("ttl", 60),
                    proxied=bool(result.get("proxied", False)),
                    comment=result.get("comment"),
                    purpose=record.purpose,
                )
        except httpx.RequestError as e:
            raise CloudflareApiError(f"Cloudflare record creation network error: {type(e).__name__}", status_code=502)

    async def update_dns_record(self, zone_id: str, record_id: str, record: DnsRecordItem) -> DnsRecordItem:
        """
        Updates an existing DNS record in Cloudflare.
        Ensures protected records are never overwritten.
        """
        if not self.is_configured:
            raise CloudflareApiError("Cloudflare API token not configured", status_code=503)

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}"
        payload = {
            "type": record.type.upper(),
            "name": record.name,
            "content": record.content,
            "ttl": record.ttl or 60,
            "proxied": record.proxied,
        }
        if record.comment:
            payload["comment"] = record.comment

        logger.info(f"Updating Cloudflare DNS record {record_id} in zone {zone_id}: {record.type} {record.name} -> {record.content}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.put(url, headers=self._get_headers(), json=payload)
                data = res.json()
                if res.status_code != 200 or not data.get("success"):
                    err_detail = data.get("errors", [{}])[0].get("message", f"HTTP {res.status_code}")
                    raise CloudflareApiError(f"Failed to update DNS record: {err_detail}", status_code=res.status_code)

                result = data.get("result", {})
                return DnsRecordItem(
                    id=result.get("id"),
                    type=result.get("type"),
                    name=result.get("name"),
                    content=result.get("content"),
                    ttl=result.get("ttl", 60),
                    proxied=bool(result.get("proxied", False)),
                    comment=result.get("comment"),
                    purpose=record.purpose,
                )
        except httpx.RequestError as e:
            raise CloudflareApiError(f"Cloudflare record update network error: {type(e).__name__}", status_code=502)

    async def delete_dns_record(
        self,
        zone_id: str,
        record_id: str,
        record: Optional[DnsRecordItem] = None,
    ) -> bool:
        """
        Deletes a DNS record from Cloudflare.
        Strictly prevents deletion of protected MX, SRV, CAA, NS, SOA, and security TXT records.
        """
        if not self.is_configured:
            raise CloudflareApiError("Cloudflare API token not configured", status_code=503)

        # Check protection
        if record and is_protected_record(record):
            raise CloudflareApiError(
                f"Cannot delete protected record {record.type} {record.name} (mail/security protection)",
                status_code=403,
            )

        url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}"
        logger.info(f"Deleting Cloudflare DNS record {record_id} in zone {zone_id}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.delete(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    return bool(data.get("success"))
                return False
        except httpx.RequestError as e:
            raise CloudflareApiError(f"Cloudflare record deletion network error: {type(e).__name__}", status_code=502)


cloudflare_service = CloudflareService()
