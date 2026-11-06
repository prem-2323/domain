import asyncio
from typing import Tuple, Optional, List
from app.models.domain import (
    DomainResult,
    DomainSearchResponse,
    DomainAvailability,
    PricingModel,
)
from app.services.validation_service import ValidationService
from app.services.registrar.factory import get_registrar_provider
from app.models.registrar import DomainAvailabilityStatus


class SearchService:
    """
    Orchestrates domain validation, .gy domain search, availability checks,
    and pricing compilation. MasterTools Domains focuses exclusively on .gy.
    """

    @classmethod
    def _generate_gy_variations(cls, sld: str) -> List[str]:
        """
        Generates smart .gy variations so users discover meaningful name options,
        all strictly ending in .gy.
        """
        variations = [
            f"{sld}.gy",
            f"get{sld}.gy",
            f"{sld}app.gy",
            f"my{sld}.gy",
            f"{sld}hq.gy",
            f"{sld}dev.gy",
            f"{sld}cloud.gy",
            f"{sld}tech.gy",
        ]
        return variations

    @classmethod
    async def search(
        cls, raw_query: str, provider_name: Optional[str] = None
    ) -> Tuple[bool, Optional[DomainSearchResponse], Optional[str]]:
        """
        Executes domain search exclusively for .gy names.
        Returns: (is_success, response_object, error_message)
        """
        is_valid, sld, explicit_tld, error_msg = ValidationService.parse_and_validate(raw_query)

        if not is_valid:
            return False, None, error_msg

        # Retrieve active registrar provider instance
        provider = get_registrar_provider(provider_name)

        # Generate target .gy names
        domains_to_check = cls._generate_gy_variations(sld)

        try:
            # Check availability via provider
            availability_results = await provider.check_bulk_availability(domains_to_check)
        except Exception:
            fallback_provider = get_registrar_provider("mock")
            availability_results = await fallback_provider.check_bulk_availability(domains_to_check)
            provider = fallback_provider

        # Fetch pricing and compile results
        async def fetch_item(check_res, is_exact: bool):
            pricing = await provider.get_pricing(check_res.domain, ".gy")

            # Status mapping
            if check_res.status == DomainAvailabilityStatus.UNAVAILABLE:
                status_enum = DomainAvailability.TAKEN
                status_label = "Unavailable / Reserved by .GY Registry"
            else:
                # All non-reserved names are explicitly marked unverified until checked with registrar
                status_enum = DomainAvailability.UNVERIFIED
                status_label = "Unverified – Real Registrar Check Required"

            pricing_model = PricingModel(
                registration_price=pricing.registration_price,
                renewal_price=pricing.renewal_price,
                currency=pricing.currency,
                discount_percent=None,  # No deceptive fake discounts
                period_years=1,
                is_mock=True,
                pricing_note="Official .GY accredited registrar estimated rate. Final price confirmed upon registrar checkout.",
            )

            # Extract SLD from domain
            item_sld = check_res.domain.replace(".gy", "")

            return DomainResult(
                domain=check_res.domain,
                name=item_sld,
                extension=".gy",
                availability=status_enum,
                price=pricing_model,
                is_exact_match=is_exact,
                status_label=status_label,
                registry="University of Guyana .GY Registry",
                features=[
                    "Official .GY Country-Code TLD",
                    "Cloudflare DNS Management",
                    "1-Click Vercel & Render DNS Sync",
                    "Accredited Registrar Fulfillment",
                ],
                is_mock=True,
            )

        items = await asyncio.gather(*(
            fetch_item(res, idx == 0) for idx, res in enumerate(availability_results)
        ))

        exact_match = items[0] if items else None
        suggestions = list(items[1:]) if len(items) > 1 else []

        disclaimer = (
            "MasterTools Domains operates exclusively with the .gy ccTLD. "
            "Availability is unverified until confirmed with an accredited .GY registrar "
            "(University of Guyana .GY Registry). No fake registrations are performed."
        )

        response = DomainSearchResponse(
            query=raw_query,
            normalized_name=sld,
            extension=".gy",
            registry="University of Guyana .GY Registry",
            official_registrars_url="https://registry.gy/registrars/",
            is_valid=True,
            exact_match=exact_match,
            suggestions=suggestions,
            total_results=len(items),
            is_mock=True,
            disclaimer=disclaimer,
        )

        return True, response, None
