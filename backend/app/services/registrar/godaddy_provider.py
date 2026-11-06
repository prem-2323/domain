from typing import List, Optional
import httpx
from app.services.registrar.base import BaseRegistrarProvider
from app.models.registrar import (
    DomainAvailabilityStatus,
    DomainCheckResult,
    DomainPriceResult,
    DomainRegisterRequest,
    DomainRegisterResult,
    DomainRenewRequest,
    DomainRenewResult,
    DomainTransferRequest,
    DomainTransferResult,
    RegistrarAuthError,
    RegistrarException,
    RegistrarNetworkError,
)
from app.core.config import settings


class GoDaddyRegistrarProvider(BaseRegistrarProvider):
    """
    GoDaddy Domain Registrar Provider.
    
    Supports both GoDaddy OTE (Operational Test Environment) and Production REST APIs.
    Endpoints:
      - OTE: https://api.ote-godaddy.com
      - Production: https://api.godaddy.com
      
    Documentation: https://developer.godaddy.com/doc/endpoint/domains
    """

    OTE_BASE_URL = "https://api.ote-godaddy.com"
    PROD_BASE_URL = "https://api.godaddy.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_sandbox: Optional[bool] = None,
    ):
        self._api_key = api_key or settings.GODADDY_API_KEY
        self._api_secret = api_secret or settings.GODADDY_API_SECRET
        self._is_sandbox = use_sandbox if use_sandbox is not None else settings.REGISTRAR_USE_SANDBOX
        self._base_url = self.OTE_BASE_URL if self._is_sandbox else self.PROD_BASE_URL

    @property
    def provider_name(self) -> str:
        return "godaddy"

    @property
    def is_sandbox(self) -> bool:
        return self._is_sandbox

    def _get_headers(self) -> dict:
        if not self._api_key or not self._api_secret:
            raise RegistrarAuthError(
                "GoDaddy API Key and Secret are not configured. Set GODADDY_API_KEY and GODADDY_API_SECRET in .env",
                provider=self.provider_name,
                error_code="MISSING_CREDENTIALS"
            )
        return {
            "Authorization": f"sso-key {self._api_key}:{self._api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _split_domain(self, domain: str) -> tuple[str, str]:
        parts = domain.lower().strip().split(".")
        if len(parts) > 1:
            return parts[0], "." + ".".join(parts[1:])
        return parts[0], ".com"

    async def check_availability(self, domain: str) -> DomainCheckResult:
        """
        Calls GoDaddy GET /v1/domains/available?domain={domain}&checkType=FAST
        """
        sld, tld = self._split_domain(domain)
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                url = f"{self._base_url}/v1/domains/available"
                response = await client.get(url, params={"domain": domain, "checkType": "FAST"}, headers=headers)

                if response.status_code == 401 or response.status_code == 403:
                    raise RegistrarAuthError(
                        "GoDaddy API authorization failed. Check your API Key and Secret.",
                        provider=self.provider_name,
                        error_code="INVALID_CREDENTIALS"
                    )

                if response.status_code != 200:
                    raise RegistrarException(
                        f"GoDaddy returned error status {response.status_code}: {response.text}",
                        provider=self.provider_name,
                        error_code="UPSTREAM_API_ERROR"
                    )

                data = response.json()
                is_available = bool(data.get("available", False))
                price_micro = data.get("price")  # In micro-units (1,000,000 = 1.00 USD)
                raw_price = (price_micro / 1000000.0) if price_micro else None

                status = DomainAvailabilityStatus.AVAILABLE if is_available else DomainAvailabilityStatus.UNAVAILABLE

                return DomainCheckResult(
                    domain=domain,
                    sld=sld,
                    tld=tld,
                    status=status,
                    is_premium=bool(data.get("definitive", False) and raw_price and raw_price > 50.0),
                    premium_price=raw_price if raw_price and raw_price > 50.0 else None,
                    currency=data.get("currency", "USD"),
                    provider=self.provider_name,
                    is_mock=False,
                )
        except httpx.RequestError as exc:
            raise RegistrarNetworkError(
                f"Failed to connect to GoDaddy API: {str(exc)}",
                provider=self.provider_name,
                error_code="CONNECTION_FAILED"
            )

    async def check_bulk_availability(self, domains: List[str]) -> List[DomainCheckResult]:
        """
        Calls GoDaddy POST /v1/domains/available with array of domains.
        """
        headers = self._get_headers()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self._base_url}/v1/domains/available"
                response = await client.post(url, json=domains, headers=headers)

                if response.status_code != 200:
                    raise RegistrarException(
                        f"GoDaddy bulk check failed ({response.status_code}): {response.text}",
                        provider=self.provider_name
                    )

                data = response.json()
                domains_list = data.get("domains", [])
                results = []
                for item in domains_list:
                    d_name = item.get("domain", "")
                    sld, tld = self._split_domain(d_name)
                    is_avail = bool(item.get("available", False))
                    price_micro = item.get("price")
                    raw_price = (price_micro / 1000000.0) if price_micro else None

                    results.append(
                        DomainCheckResult(
                            domain=d_name,
                            sld=sld,
                            tld=tld,
                            status=DomainAvailabilityStatus.AVAILABLE if is_avail else DomainAvailabilityStatus.UNAVAILABLE,
                            is_premium=bool(raw_price and raw_price > 50.0),
                            premium_price=raw_price if raw_price and raw_price > 50.0 else None,
                            currency=item.get("currency", "USD"),
                            provider=self.provider_name,
                            is_mock=False,
                        )
                    )
                return results
        except httpx.RequestError as exc:
            raise RegistrarNetworkError(
                f"Failed to connect to GoDaddy API: {str(exc)}",
                provider=self.provider_name
            )

    async def get_pricing(self, domain: str, tld: str) -> DomainPriceResult:
        check = await self.check_availability(domain)
        base_price = check.premium_price or 14.99
        return DomainPriceResult(
            domain=domain,
            tld=tld or check.tld,
            registration_price=base_price,
            renewal_price=base_price * 1.25,
            currency=check.currency,
            period_years=1,
            provider=self.provider_name,
            is_mock=False,
        )

    async def register_domain(self, request: DomainRegisterRequest) -> DomainRegisterResult:
        """
        Domain purchase structure prepared for GoDaddy POST /v1/domains/purchase.
        NOTE: Controlled execution guard prevents unintended financial commitments.
        """
        # Ensure credentials are valid
        self._get_headers()

        # Architecture requirement: Do not make live purchase charges during testing without explicit confirmation
        raise RegistrarException(
            "Live domain registration API call intercepted by safety guard. "
            "To test order workflows safely, switch to REGISTRAR_PROVIDER=mock.",
            provider=self.provider_name,
            error_code="PURCHASE_ACTION_GUARD"
        )

    async def renew_domain(self, request: DomainRenewRequest) -> DomainRenewResult:
        self._get_headers()
        raise RegistrarException(
            "Live renewal API call intercepted by safety guard. Switch to REGISTRAR_PROVIDER=mock for demo renewals.",
            provider=self.provider_name,
            error_code="RENEWAL_ACTION_GUARD"
        )

    async def transfer_domain(self, request: DomainTransferRequest) -> DomainTransferResult:
        self._get_headers()
        raise RegistrarException(
            "Live transfer API call intercepted by safety guard. Switch to REGISTRAR_PROVIDER=mock for demo transfers.",
            provider=self.provider_name,
            error_code="TRANSFER_ACTION_GUARD"
        )
