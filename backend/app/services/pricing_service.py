from app.models.domain import DomainAvailability, PricingModel
from app.services.catalog_service import CatalogService


class PricingService:
    """
    Mock pricing calculation service.
    
    Provides simulated registration and renewal prices based on TLD catalogue rates
    and domain tier (standard vs premium).
    """

    @classmethod
    def get_pricing(
        cls,
        name: str,
        extension: str,
        availability: DomainAvailability,
    ) -> PricingModel:
        """
        Generates simulated pricing for a given domain and extension.
        """
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
            # Deterministic multiplier for premium valuation
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
            pricing_note="Estimated accredited registrar rate (~$45.00/yr). Final price confirmed upon registrar quote.",
        )
