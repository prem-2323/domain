from typing import List, Optional
import xml.etree.ElementTree as ET
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


class NamecheapRegistrarProvider(BaseRegistrarProvider):
    """
    Namecheap Domain Registrar Provider (XML API).
    
    Endpoints:
      - Sandbox: https://api.sandbox.namecheap.com/xml.response
      - Production: https://api.namecheap.com/xml.response
      
    NOTE: Namecheap requires your server's public IP (ClientIP) to be whitelisted
    in your Namecheap Profile -> Tools -> API Access.
    """

    SANDBOX_URL = "https://api.sandbox.namecheap.com/xml.response"
    PROD_URL = "https://api.namecheap.com/xml.response"

    def __init__(
        self,
        api_user: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        client_ip: Optional[str] = None,
        use_sandbox: Optional[bool] = None,
    ):
        self._api_user = api_user or settings.NAMECHEAP_API_USER
        self._api_key = api_key or settings.NAMECHEAP_API_KEY
        self._username = username or settings.NAMECHEAP_USERNAME or self._api_user
        self._client_ip = client_ip or settings.NAMECHEAP_CLIENT_IP
        self._is_sandbox = use_sandbox if use_sandbox is not None else settings.REGISTRAR_USE_SANDBOX
        self._base_url = self.SANDBOX_URL if self._is_sandbox else self.PROD_URL

    @property
    def provider_name(self) -> str:
        return "namecheap"

    @property
    def is_sandbox(self) -> bool:
        return self._is_sandbox

    def _get_base_params(self, command: str) -> dict:
        if not self._api_user or not self._api_key or not self._client_ip:
            raise RegistrarAuthError(
                "Namecheap credentials missing. Set NAMECHEAP_API_USER, NAMECHEAP_API_KEY, and NAMECHEAP_CLIENT_IP in .env",
                provider=self.provider_name,
                error_code="MISSING_CREDENTIALS"
            )
        return {
            "ApiUser": self._api_user,
            "ApiKey": self._api_key,
            "UserName": self._username,
            "ClientIP": self._client_ip,
            "Command": command,
        }

    def _split_domain(self, domain: str) -> tuple[str, str]:
        parts = domain.lower().strip().split(".")
        if len(parts) > 1:
            return parts[0], "." + ".".join(parts[1:])
        return parts[0], ".com"

    async def check_availability(self, domain: str) -> DomainCheckResult:
        """
        Executes namecheap.domains.check for single domain.
        """
        results = await self.check_bulk_availability([domain])
        if results:
            return results[0]
        sld, tld = self._split_domain(domain)
        return DomainCheckResult(
            domain=domain,
            sld=sld,
            tld=tld,
            status=DomainAvailabilityStatus.UNKNOWN,
            provider=self.provider_name,
            is_mock=False,
        )

    async def check_bulk_availability(self, domains: List[str]) -> List[DomainCheckResult]:
        """
        Executes namecheap.domains.check with comma-separated DomainList.
        """
        params = self._get_base_params("namecheap.domains.check")
        params["DomainList"] = ",".join(domains)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._base_url, params=params)
                if response.status_code != 200:
                    raise RegistrarException(
                        f"Namecheap HTTP status {response.status_code}: {response.text}",
                        provider=self.provider_name
                    )

                # Parse XML Response
                root = ET.fromstring(response.content)
                # Namecheap XML namespace handling
                namespaces = {"nc": "http://api.namecheap.com/xml.response"}

                errors = root.findall(".//nc:Errors/nc:Error", namespaces)
                if errors:
                    err_msg = "; ".join([e.text or "" for e in errors])
                    if "IP" in err_msg or "whitelist" in err_msg.lower():
                        raise RegistrarAuthError(
                            f"Namecheap IP Authorization failed: {err_msg}",
                            provider=self.provider_name,
                            error_code="IP_NOT_WHITELISTED"
                        )
                    raise RegistrarException(
                        f"Namecheap Error: {err_msg}",
                        provider=self.provider_name
                    )

                results = []
                domain_elements = root.findall(".//nc:DomainCheckResult", namespaces)
                for el in domain_elements:
                    d_name = el.get("Domain", "")
                    available_str = el.get("Available", "false").lower()
                    is_avail = available_str == "true"
                    is_prem = el.get("IsPremiumName", "false").lower() == "true"
                    prem_price = float(el.get("PremiumRegistrationPrice", 0.0)) if is_prem else None

                    sld, tld = self._split_domain(d_name)
                    status = (
                        DomainAvailabilityStatus.PREMIUM if is_prem else
                        DomainAvailabilityStatus.AVAILABLE if is_avail else
                        DomainAvailabilityStatus.UNAVAILABLE
                    )

                    results.append(
                        DomainCheckResult(
                            domain=d_name,
                            sld=sld,
                            tld=tld,
                            status=status,
                            is_premium=is_prem,
                            premium_price=prem_price,
                            currency="USD",
                            provider=self.provider_name,
                            is_mock=False,
                        )
                    )
                return results

        except httpx.RequestError as exc:
            raise RegistrarNetworkError(
                f"Failed to connect to Namecheap API: {str(exc)}",
                provider=self.provider_name
            )
        except ET.ParseError as exc:
            raise RegistrarException(
                f"Failed to parse Namecheap XML response: {str(exc)}",
                provider=self.provider_name
            )

    async def get_pricing(self, domain: str, tld: str) -> DomainPriceResult:
        sld, parsed_tld = self._split_domain(domain)
        target_tld = tld or parsed_tld
        check = await self.check_availability(domain)
        base_price = check.premium_price or 11.98

        return DomainPriceResult(
            domain=domain,
            tld=target_tld,
            registration_price=base_price,
            renewal_price=base_price * 1.3,
            transfer_price=base_price,
            currency="USD",
            period_years=1,
            provider=self.provider_name,
            is_mock=False,
        )

    async def register_domain(self, request: DomainRegisterRequest) -> DomainRegisterResult:
        self._get_base_params("namecheap.domains.create")
        raise RegistrarException(
            "Live domain registration API call intercepted by safety guard. "
            "To test order workflows safely, switch to REGISTRAR_PROVIDER=mock.",
            provider=self.provider_name,
            error_code="PURCHASE_ACTION_GUARD"
        )

    async def renew_domain(self, request: DomainRenewRequest) -> DomainRenewResult:
        self._get_base_params("namecheap.domains.renew")
        raise RegistrarException(
            "Live renewal API call intercepted by safety guard. Switch to REGISTRAR_PROVIDER=mock for demo renewals.",
            provider=self.provider_name,
            error_code="RENEWAL_ACTION_GUARD"
        )

    async def transfer_domain(self, request: DomainTransferRequest) -> DomainTransferResult:
        self._get_base_params("namecheap.domains.transfer.create")
        raise RegistrarException(
            "Live transfer API call intercepted by safety guard. Switch to REGISTRAR_PROVIDER=mock for demo transfers.",
            provider=self.provider_name,
            error_code="TRANSFER_ACTION_GUARD"
        )
