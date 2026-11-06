from typing import List, Dict, Any, Optional


class CatalogService:
    """
    Manages top-level domain (TLD) extension definitions and metadata.
    MasterTools Domains focuses exclusively on the .gy top-level domain.
    """

    EXTENSIONS_METADATA: Dict[str, Dict[str, Any]] = {
        ".gy": {
            "category": "ccTLD",
            "registry": "University of Guyana .GY Registry",
            "official_directory": "https://registry.gy/registrars/",
            "base_registration": 45.00,
            "base_renewal": 45.00,
            "popular": True,
            "description": "Official country-code domain for Guyana (.gy)",
            "status_notice": "Unverified – Availability must be confirmed via an accredited .GY registrar",
        }
    }

    # MasterTools Domains exclusively offers .gy
    DEFAULT_TLD_ORDER = [".gy"]

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Returns all supported extension strings (.gy only)."""
        return list(cls.DEFAULT_TLD_ORDER)

    @classmethod
    def get_catalog_details(cls) -> List[Dict[str, Any]]:
        """Returns detailed .gy extension metadata."""
        return [
            {"extension": tld, **cls.EXTENSIONS_METADATA.get(tld, {})}
            for tld in cls.DEFAULT_TLD_ORDER
        ]

    @classmethod
    def is_supported(cls, tld: str) -> bool:
        """Checks if an extension is supported (.gy only)."""
        return tld.lower() == ".gy"

    @classmethod
    def get_ordered_extensions(cls, explicit_tld: Optional[str] = None) -> List[str]:
        """Returns ['.gy'] as the single supported extension."""
        return list(cls.DEFAULT_TLD_ORDER)
