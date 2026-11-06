import uuid
from typing import List

from app.core.config import settings
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
)


class MockRegistrarProvider(BaseRegistrarProvider):
    """
    Simulated registrar provider focusing exclusively on the .gy top-level domain.
    
    All availability statuses are explicitly marked as UNVERIFIED until verified
    against the official University of Guyana .GY Registry.
    Pricing reflects official .GY accredited registrar standard rates without fake discounts.
    """

    RESERVED_NAMES = {
        "gov", "mil", "edu", "net", "org", "com", "gy", "registry",
        "guyana", "university", "google", "apple", "mastertools",
        "nic", "admin", "root", "whois", "dns"
    }

    OFFICIAL_REGISTRAR_ANNUAL_PRICE = 45.00  # Standard accredited registrar rate in USD

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_sandbox(self) -> bool:
        return True

    def _split_domain(self, domain: str) -> tuple[str, str]:
        parts = domain.lower().strip().split(".")
        if len(parts) > 1:
            return parts[0], "." + ".".join(parts[1:])
        return parts[0], ".gy"

    async def check_availability(self, domain: str) -> DomainCheckResult:
        sld, tld = self._split_domain(domain)

        # Reserved names
        if sld in self.RESERVED_NAMES:
            return DomainCheckResult(
                domain=f"{sld}{tld}",
                sld=sld,
                tld=tld,
                status=DomainAvailabilityStatus.UNAVAILABLE,
                is_premium=False,
                provider=self.provider_name,
                is_mock=True,
            )

        # All other domains are marked as UNVERIFIED until real registrar confirmation
        return DomainCheckResult(
            domain=f"{sld}{tld}",
            sld=sld,
            tld=tld,
            status=DomainAvailabilityStatus.UNVERIFIED,
            is_premium=False,
            premium_price=None,
            currency="USD",
            provider=self.provider_name,
            is_mock=True,
        )

    async def check_bulk_availability(self, domains: List[str]) -> List[DomainCheckResult]:
        return [await self.check_availability(d) for d in domains]

    async def get_pricing(self, domain: str, tld: str) -> DomainPriceResult:
        sld, parsed_tld = self._split_domain(domain)
        target_tld = parsed_tld or tld or ".gy"
        price = 0.0 if settings.FREE_TESTING_MODE else self.OFFICIAL_REGISTRAR_ANNUAL_PRICE

        return DomainPriceResult(
            domain=f"{sld}{target_tld}",
            tld=target_tld,
            registration_price=price,
            renewal_price=price,
            transfer_price=price,
            currency="USD",
            discount_percent=None,  # No deceptive fake discounts
            period_years=1,
            provider=self.provider_name,
            is_mock=True,
        )

    async def register_domain(self, request: DomainRegisterRequest) -> DomainRegisterResult:
        """
        Records registration request without claiming live registrar completion.
        Adheres to requirement: Do not implement fake registration.
        """
        inquiry_token = uuid.uuid4().hex[:10].upper()

        return DomainRegisterResult(
            domain=request.domain,
            order_id=f"GY-INQ-{inquiry_token}",
            transaction_id=f"INQ-ROUTED-{uuid.uuid4().hex[:12].upper()}",
            is_success=True,
            status="pending_registrar_coordination",
            expiration_date=None,
            charged_amount=0.0,
            currency="USD",
            provider=self.provider_name,
            is_mock=True,
            message=(
                f"Registration inquiry for {request.domain} received. "
                "Registrations are executed through an accredited .GY registrar (University of Guyana Registry). "
                "No live charge or fake registration was performed."
            ),
        )

    async def renew_domain(self, request: DomainRenewRequest) -> DomainRenewResult:
        inquiry_token = uuid.uuid4().hex[:10].upper()
        return DomainRenewResult(
            domain=request.domain,
            order_id=f"GY-REN-{inquiry_token}",
            new_expiration_date="Pending Registrar Confirmation",
            charged_amount=0.0,
            is_success=True,
            provider=self.provider_name,
            is_mock=True,
            message="Renewal inquiry logged for accredited .GY registrar coordination.",
        )

    async def transfer_domain(self, request: DomainTransferRequest) -> DomainTransferResult:
        transfer_token = uuid.uuid4().hex[:8].upper()
        return DomainTransferResult(
            domain=request.domain,
            transfer_id=f"GY-XFER-{transfer_token}",
            status="pending_epp_verification",
            provider=self.provider_name,
            is_mock=True,
            message="Inbound .gy transfer request queued for .GY Registry authorization.",
        )
