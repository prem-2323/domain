from app.models.domain import DomainAvailability, PricingModel
from app.services.catalog_service import CatalogService
from app.core.config import settings


class PricingService:
    """
    Pricing calculation service.
    In Free Testing Mode, registration and renewal prices are strictly $0.00 / Free.
    """

    @classmethod
    def get_pricing(
        cls,
        name: str,
        extension: str,
        availability: DomainAvailability,
    ) -> PricingModel:
        """
        Generates pricing for a given domain and extension.
        Enforces $0.00 / Free Testing Mode when enabled.
        """
        if settings.FREE_TESTING_MODE:
            return PricingModel(
                registration_price=0.0,
                renewal_price=0.0,
                currency="USD",
                discount_percent=None,
                period_years=1,
                is_mock=True,
                pricing_note=settings.FREE_TESTING_DISCLAIMER,
            )

        metadata = CatalogService.EXTENSIONS_METADATA.get(
            extension.lower(),
            {
                "base_registration": 14.99,
                "base_renewal": 19.99,
            }
        )

        base_reg = float(metadata.get("base_registration", 14.99))
        base_renewal = float(metadata.get("base_renewal", 19.99))

        if availability == DomainAvailability.PREMIUM:
            multiplier = 8.0 if len(name) <= 3 else 4.5
            premium_price = round(base_reg * multiplier, 2)
            return PricingModel(
                registration_price=premium_price,
                renewal_price=base_renewal,
                currency="USD",
                discount_percent=None,
                period_years=1,
                is_mock=True,
            )

        if availability == DomainAvailability.TAKEN:
            return PricingModel(
                registration_price=0.0,
                renewal_price=base_renewal,
                currency="USD",
                discount_percent=None,
                period_years=1,
                is_mock=True,
            )

        return PricingModel(
            registration_price=base_reg,
            renewal_price=base_renewal,
            currency="USD",
            discount_percent=None,
            period_years=1,
            is_mock=True,
            pricing_note="Standard accredited registrar rate. Final price confirmed upon registrar quote.",
        )
