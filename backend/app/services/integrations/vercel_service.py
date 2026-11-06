import logging
from typing import List, Optional, Dict, Any, Tuple
import httpx

from app.core.config import settings
from app.models.integration import DnsRecordItem

logger = logging.getLogger("vercel_service")

VERCEL_API_BASE = "https://api.vercel.com"


class VercelApiError(Exception):
    def __init__(self, message: str, status_code: int = 502, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class VercelService:
    """
    Real Vercel API client for project domain addition, required DNS retrieval,
    and domain configuration verification.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        self._api_token = api_token or settings.VERCEL_API_TOKEN
        self.project_id = project_id or settings.VERCEL_PROJECT_ID
        self.team_id = team_id or settings.VERCEL_TEAM_ID
        self.timeout = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(
            self._api_token
            and self._api_token.strip()
            and self.project_id
            and self.project_id.strip()
        )

    def _get_headers(self) -> Dict[str, str]:
        if not self._api_token or not self._api_token.strip():
            raise VercelApiError("Vercel API token is not configured on the backend.", status_code=503)
        return {
            "Authorization": f"Bearer {self._api_token.strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if self.team_id and self.team_id.strip():
            params["teamId"] = self.team_id.strip()
        if extra:
            params.update(extra)
        return params

    async def verify_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Verifies Vercel API token and project ID existence.
        """
        if not self.is_configured:
            return False, "Vercel API token or Project ID not configured"

        url = f"{VERCEL_API_BASE}/v9/projects/{self.project_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers(), params=self._get_params())
                if res.status_code == 200:
                    data = res.json()
                    return True, data.get("name")
                elif res.status_code in (401, 403):
                    return False, "Invalid or unauthorized Vercel API token"
                elif res.status_code == 404:
                    return False, f"Vercel project '{self.project_id}' not found"
                return False, f"Unexpected response ({res.status_code})"
        except httpx.RequestError as e:
            logger.warning(f"Vercel verification request error: {type(e).__name__}")
            return False, f"Network error: {type(e).__name__}"

    async def add_domain_to_project(self, domain: str) -> Dict[str, Any]:
        """
        Adds a custom domain to the Vercel project via POST /v9/projects/{projectId}/domains.
        """
        if not self.is_configured:
            raise VercelApiError("Vercel integration is not configured", status_code=503)

        url = f"{VERCEL_API_BASE}/v9/projects/{self.project_id}/domains"
        payload = {"name": domain.strip().lower()}
        logger.info(f"Adding domain '{domain}' to Vercel project '{self.project_id}'")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=self._get_headers(), params=self._get_params(), json=payload)
                data = res.json()
                if res.status_code in (200, 201):
                    return data
                # If domain already added to project (code: 'domain_already_in_use' or similar), fetch existing
                if res.status_code == 409 or "already" in str(data).lower():
                    existing = await self.get_project_domain(domain)
                    if existing:
                        return existing
                err_msg = data.get("error", {}).get("message", f"HTTP {res.status_code}")
                raise VercelApiError(f"Failed to add domain to Vercel project: {err_msg}", status_code=res.status_code, detail=data)
        except httpx.RequestError as e:
            raise VercelApiError(f"Vercel API network error: {type(e).__name__}", status_code=502)

    async def get_project_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves project domain details from Vercel via GET /v9/projects/{projectId}/domains/{domain}.
        """
        if not self.is_configured:
            return None

        url = f"{VERCEL_API_BASE}/v9/projects/{self.project_id}/domains/{domain.strip().lower()}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers(), params=self._get_params())
                if res.status_code == 200:
                    return res.json()
                return None
        except Exception as e:
            logger.warning(f"Error fetching Vercel project domain {domain}: {e}")
            return None

    async def get_domain_config(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves exact DNS configuration recommended by Vercel via GET /v6/domains/{domain}/config.
        """
        if not self._api_token:
            return None

        url = f"{VERCEL_API_BASE}/v6/domains/{domain.strip().lower()}/config"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers(), params=self._get_params())
                if res.status_code == 200:
                    return res.json()
                return None
        except Exception:
            return None

    async def get_required_dns_records(self, domain: str) -> List[DnsRecordItem]:
        """
        Determines exact DNS records required by Vercel for this domain.
        Never invents verification TXT records or IPs.
        """
        records: List[DnsRecordItem] = []
        dom = domain.strip().lower()
        parts = dom.split(".")
        is_apex = len(parts) == 2

        # 1. Fetch domain config from Vercel
        config = await self.get_domain_config(dom)
        rec_ipv4 = "76.76.21.21"
        rec_cname = "cname.vercel-dns.com"
        if config:
            rec_ipv4 = config.get("recommendedIPv4") or rec_ipv4
            rec_cname = config.get("recommendedCNAME") or rec_cname

        if is_apex:
            # Apex domain requires A record on @
            records.append(
                DnsRecordItem(
                    type="A",
                    name="@",
                    content=rec_ipv4,
                    ttl=60,
                    proxied=False,
                    purpose="Vercel Edge Network root routing",
                )
            )
            # Standard www CNAME
            records.append(
                DnsRecordItem(
                    type="CNAME",
                    name="www",
                    content=rec_cname,
                    ttl=60,
                    proxied=False,
                    purpose="Vercel www subdomain routing",
                )
            )
        else:
            # Subdomain requires CNAME pointing to cname.vercel-dns.com
            sublabel = parts[0]
            records.append(
                DnsRecordItem(
                    type="CNAME",
                    name=sublabel,
                    content=rec_cname,
                    ttl=60,
                    proxied=False,
                    purpose="Vercel subdomain routing",
                )
            )

        # 2. Check for actual verification challenge required by Vercel
        proj_domain = await self.get_project_domain(dom)
        if proj_domain:
            verification = proj_domain.get("verification") or []
            for v in verification:
                v_type = v.get("type", "TXT").upper()
                v_domain = v.get("domain", f"_vercel.{dom}")
                v_value = v.get("value")
                # Format record name relative to zone
                v_name = v_domain.replace(f".{dom}", "") if v_domain.endswith(f".{dom}") else v_domain
                if v_value:
                    records.append(
                        DnsRecordItem(
                            type=v_type,
                            name=v_name,
                            content=v_value,
                            ttl=60,
                            proxied=False,
                            purpose=f"Vercel domain verification challenge ({v.get('reason', 'ownership')})",
                        )
                    )

        return records

    async def verify_domain(self, domain: str) -> Dict[str, Any]:
        """
        Triggers Vercel verification check for the domain via POST /v9/projects/{projectId}/domains/{domain}/verify.
        """
        if not self.is_configured:
            raise VercelApiError("Vercel integration is not configured", status_code=503)

        url = f"{VERCEL_API_BASE}/v9/projects/{self.project_id}/domains/{domain.strip().lower()}/verify"
        logger.info(f"Triggering Vercel domain verification for '{domain}'")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=self._get_headers(), params=self._get_params())
                data = res.json()
                if res.status_code == 200:
                    return data
                err_msg = data.get("error", {}).get("message", f"HTTP {res.status_code}")
                raise VercelApiError(f"Vercel verification failed: {err_msg}", status_code=res.status_code, detail=data)
        except httpx.RequestError as e:
            raise VercelApiError(f"Vercel verify network error: {type(e).__name__}", status_code=502)


vercel_service = VercelService()
