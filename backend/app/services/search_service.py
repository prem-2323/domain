import asyncio
from typing import Tuple, Optional, List
from app.core.config import settings
from app.models.domain import (
    DomainResult,
    DomainSearchResponse,
    DomainAvailability,
    PricingModel,
)
from app.services.validation_service import ValidationService
from app.services.catalog_service import CatalogService
from app.services.registrar.factory import get_registrar_provider
from app.models.registrar import DomainAvailabilityStatus


class SearchService:
    """
    Orchestrates domain validation, multi-TLD domain search, availability checks,
    and pricing compilation in Free Testing Mode.
    """

    @classmethod
    def _generate_variations(cls, sld: str, explicit_tld: Optional[str] = None) -> List[str]:
        """
        Generates smart variations across supported extensions (.gy, .com, .in, .org, .net, etc.).
        """
        supported_exts = CatalogService.get_ordered_extensions(explicit_tld)
        primary_tld = explicit_tld or supported_exts[0]

        variations: List[str] = []

        # 1. Exact name across top extensions
        variations.append(f"{sld}{primary_tld}")
        for ext in supported_exts:
            dom = f"{sld}{ext}"
            if dom not in variations:
                variations.append(dom)

        # 2. Helpful keyword variations for the primary TLD
        keyword_prefixes = ["get", "my"]
        keyword_suffixes = ["app", "hq", "dev", "tech"]

        for pre in keyword_prefixes:
            dom = f"{pre}{sld}{primary_tld}"
            if dom not in variations and len(variations) < 12:
                variations.append(dom)

        for suf in keyword_suffixes:
            dom = f"{sld}{suf}{primary_tld}"
            if dom not in variations and len(variations) < 12:
                variations.append(dom)

        return variations

    @classmethod
    async def search(
        cls, raw_query: str, provider_name: Optional[str] = None
    ) -> Tuple[bool, Optional[DomainSearchResponse], Optional[str]]:
        """
        Executes domain search across configured extensions in Free Testing Mode.
        Returns: (is_success, response_object, error_message)
        """
        is_valid, sld, explicit_tld, error_msg = ValidationService.parse_and_validate(raw_query)

        if not is_valid:
            return False, None, error_msg

        # Retrieve active registrar provider instance
        provider = get_registrar_provider(provider_name)

        # Generate target names across extensions
        domains_to_check = cls._generate_variations(sld, explicit_tld)

        try:
            # Check availability via provider
            availability_results = await provider.check_bulk_availability(domains_to_check)
        except Exception:
            fallback_provider = get_registrar_provider("mock")
            availability_results = await fallback_provider.check_bulk_availability(domains_to_check)
            provider = fallback_provider

        # Fetch pricing and compile results
        async def fetch_item(check_res, is_exact: bool):
            domain_str = check_res.domain
            parts = domain_str.split(".")
            item_sld = parts[0]
            item_tld = "." + ".".join(parts[1:]) if len(parts) > 1 else ".com"

            pricing = await provider.get_pricing(domain_str, item_tld)

            # Registry metadata for this extension
            cat_meta = CatalogService.EXTENSIONS_METADATA.get(item_tld, {})
            registry_name = cat_meta.get("registry", "Accredited Registry Authority")

            # Status mapping
            if check_res.status == DomainAvailabilityStatus.UNAVAILABLE:
                status_enum = DomainAvailability.TAKEN
                status_label = f"Unavailable / Reserved ({item_tld} Registry)"
            else:
                status_enum = DomainAvailability.UNVERIFIED
                status_label = "Unverified – Real Registrar Check Required"

            # In Free Testing Mode, all pricing is $0.00 / Free
            reg_price = 0.0 if settings.FREE_TESTING_MODE else pricing.registration_price
            ren_price = 0.0 if settings.FREE_TESTING_MODE else pricing.renewal_price

            pricing_model = PricingModel(
                registration_price=reg_price,
                renewal_price=ren_price,
                currency=pricing.currency,
                discount_percent=None,
                period_years=1,
                is_mock=True,
                pricing_note=(
                    settings.FREE_TESTING_DISCLAIMER
                    if settings.FREE_TESTING_MODE
                    else f"Standard {item_tld} accredited registrar estimated rate."
                ),
            )

            return DomainResult(
                domain=domain_str,
                name=item_sld,
                extension=item_tld,
                availability=status_enum,
                price=pricing_model,
                is_exact_match=is_exact,
                status_label=status_label,
                registry=registry_name,
                features=[
                    f"Official {item_tld} TLD Namespace",
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

        disclaimer = settings.FREE_TESTING_DISCLAIMER if settings.FREE_TESTING_MODE else (
            "Availability is unverified until confirmed with an accredited registrar. "
            "No fake registrations are performed."
        )

        primary_extension = explicit_tld or (exact_match.extension if exact_match else ".com")
        primary_registry = CatalogService.EXTENSIONS_METADATA.get(
            primary_extension, {}
        ).get("registry", "Accredited Registry Authority")
        official_url = CatalogService.EXTENSIONS_METADATA.get(
            primary_extension, {}
        ).get("official_directory", "https://www.icann.org/")

        response = DomainSearchResponse(
            query=raw_query,
            normalized_name=sld,
            extension=primary_extension,
            registry=primary_registry,
            official_registrars_url=official_url,
            is_valid=True,
            exact_match=exact_match,
            suggestions=suggestions,
            total_results=len(items),
            is_mock=True,
            disclaimer=disclaimer,
        )

        return True, response, None
