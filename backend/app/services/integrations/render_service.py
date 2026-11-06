import logging
from typing import List, Optional, Dict, Any, Tuple
import httpx

from app.core.config import settings
from app.models.integration import DnsRecordItem

logger = logging.getLogger("render_service")

RENDER_API_BASE = "https://api.render.com/v1"


class RenderApiError(Exception):
    def __init__(self, message: str, status_code: int = 502, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class RenderService:
    """
    Real Render API client for web service inspection, custom domain registration,
    and domain verification.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        service_id: Optional[str] = None,
    ):
        self._api_key = api_key or settings.RENDER_API_KEY
        self.service_id = service_id or settings.RENDER_SERVICE_ID
        self.timeout = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(
            self._api_key
            and self._api_key.strip()
            and self.service_id
            and self.service_id.strip()
        )

    def _get_headers(self) -> Dict[str, str]:
        if not self._api_key or not self._api_key.strip():
            raise RenderApiError("Render API key is not configured on the backend.", status_code=503)
        return {
            "Authorization": f"Bearer {self._api_key.strip()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def verify_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Verifies Render API key and service ID existence via GET /v1/services/{serviceId}.
        """
        if not self.is_configured:
            return False, "Render API key or Service ID not configured"

        url = f"{RENDER_API_BASE}/services/{self.service_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    service_name = data.get("service", {}).get("name") or data.get("name")
                    return True, service_name
                elif res.status_code in (401, 403):
                    return False, "Invalid or unauthorized Render API key"
                elif res.status_code == 404:
                    return False, f"Render service '{self.service_id}' not found"
                return False, f"Unexpected response ({res.status_code})"
        except httpx.RequestError as e:
            logger.warning(f"Render verification request error: {type(e).__name__}")
            return False, f"Network error: {type(e).__name__}"

    async def get_service(self) -> Dict[str, Any]:
        """
        Retrieves service details (including slug / onrender.com address).
        """
        if not self.is_configured:
            raise RenderApiError("Render integration is not configured", status_code=503)

        url = f"{RENDER_API_BASE}/services/{self.service_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    return res.json()
                err_msg = res.json().get("message", f"HTTP {res.status_code}")
                raise RenderApiError(f"Failed to get Render service: {err_msg}", status_code=res.status_code)
        except httpx.RequestError as e:
            raise RenderApiError(f"Render network error: {type(e).__name__}", status_code=502)

    async def add_custom_domain(self, domain: str) -> Dict[str, Any]:
        """
        Registers a custom domain with the Render service via POST /v1/services/{serviceId}/custom-domains.
        """
        if not self.is_configured:
            raise RenderApiError("Render integration is not configured", status_code=503)

        url = f"{RENDER_API_BASE}/services/{self.service_id}/custom-domains"
        payload = {"name": domain.strip().lower()}
        logger.info(f"Adding custom domain '{domain}' to Render service '{self.service_id}'")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                data = res.json()
                if res.status_code in (200, 201):
                    return data
                # If domain already added, retrieve existing
                if res.status_code == 409 or "already" in str(data).lower():
                    existing = await self.get_custom_domain(domain)
                    if existing:
                        return existing
                err_msg = data.get("message", f"HTTP {res.status_code}")
                raise RenderApiError(f"Failed to add custom domain to Render: {err_msg}", status_code=res.status_code, detail=data)
        except httpx.RequestError as e:
            raise RenderApiError(f"Render custom domain network error: {type(e).__name__}", status_code=502)

    async def get_custom_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves custom domain details from Render via GET /v1/services/{serviceId}/custom-domains/{domain}.
        """
        if not self.is_configured:
            return None

        url = f"{RENDER_API_BASE}/services/{self.service_id}/custom-domains/{domain.strip().lower()}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    return res.json()
                return None
        except Exception:
            return None

    async def get_required_dns_records(self, domain: str) -> List[DnsRecordItem]:
        """
        Retrieves exact DNS records required by Render for this domain.
        Queries the service slug for the exact onrender.com host.
        """
        records: List[DnsRecordItem] = []
        dom = domain.strip().lower()
        parts = dom.split(".")
        is_apex = len(parts) == 2

        # 1. Get service details for actual slug
        service_data = await self.get_service()
        service_obj = service_data.get("service") or service_data
        service_slug = service_obj.get("slug") or service_obj.get("name", "app")
        render_target = f"{service_slug}.onrender.com"

        # 2. Check if custom domain already exists and has specific dnsRecords
        custom_dom = await self.get_custom_domain(dom)
        if custom_dom and custom_dom.get("dnsRecords"):
            for rec in custom_dom["dnsRecords"]:
                records.append(
                    DnsRecordItem(
                        type=rec.get("type", "CNAME"),
                        name=rec.get("name", "@" if is_apex else parts[0]),
                        content=rec.get("value", render_target),
                        ttl=60,
                        proxied=False,
                        purpose=rec.get("purpose", "Render Web Service endpoint"),
                    )
                )
            return records

        if is_apex:
            # Apex domain: CNAME flattening on @ (or ALIAS)
            records.append(
                DnsRecordItem(
                    type="CNAME",
                    name="@",
                    content=render_target,
                    ttl=60,
                    proxied=False,
                    purpose="Render Web Service root endpoint (Cloudflare CNAME flattening)",
                )
            )
            # www subdomain CNAME
            records.append(
                DnsRecordItem(
                    type="CNAME",
                    name="www",
                    content=render_target,
                    ttl=60,
                    proxied=False,
                    purpose="Render Web Service www endpoint",
                )
            )
        else:
            # Subdomain
            records.append(
                DnsRecordItem(
                    type="CNAME",
                    name=parts[0],
                    content=render_target,
                    ttl=60,
                    proxied=False,
                    purpose="Render Web Service subdomain endpoint",
                )
            )

        return records

    async def verify_custom_domain(self, domain: str) -> Dict[str, Any]:
        """
        Triggers Render verification check for the custom domain via POST /v1/services/{serviceId}/custom-domains/{domain}/verify.
        """
        if not self.is_configured:
            raise RenderApiError("Render integration is not configured", status_code=503)

        url = f"{RENDER_API_BASE}/services/{self.service_id}/custom-domains/{domain.strip().lower()}/verify"
        logger.info(f"Triggering Render custom domain verification for '{domain}'")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=self._get_headers())
                data = res.json()
                if res.status_code in (200, 202):
                    return data
                err_msg = data.get("message", f"HTTP {res.status_code}")
                raise RenderApiError(f"Render domain verification failed: {err_msg}", status_code=res.status_code, detail=data)
        except httpx.RequestError as e:
            raise RenderApiError(f"Render verify network error: {type(e).__name__}", status_code=502)


render_service = RenderService()
