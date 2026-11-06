from typing import List, Dict, Any, Optional
from app.core.config import settings


class CatalogService:
    """
    Manages top-level domain (TLD) extension definitions and metadata.
    Supports .gy, .com, .in, .org, .net, and popular extensions in Free Testing Mode.
    """

    EXTENSIONS_METADATA: Dict[str, Dict[str, Any]] = {
        ".gy": {
            "category": "ccTLD",
            "registry": "University of Guyana .GY Registry",
            "official_directory": "https://registry.gy/registrars/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Official country-code domain for Guyana (.gy)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".com": {
            "category": "gTLD",
            "registry": "VeriSign Global Registry",
            "official_directory": "https://www.verisign.com/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "World's most recognized top-level domain (.com)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".in": {
            "category": "ccTLD",
            "registry": "National Internet Exchange of India (.IN Registry)",
            "official_directory": "https://registry.in/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Official country-code domain for India (.in)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".org": {
            "category": "gTLD",
            "registry": "Public Interest Registry (PIR)",
            "official_directory": "https://thenew.org/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Trusted domain for organizations and communities (.org)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".net": {
            "category": "gTLD",
            "registry": "VeriSign Global Registry",
            "official_directory": "https://www.verisign.com/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Classic infrastructure and networking domain (.net)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".co": {
            "category": "ccTLD / Global",
            "registry": ".CO Internet S.A.S.",
            "official_directory": "https://www.go.co/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Modern domain for innovators and companies (.co)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".io": {
            "category": "ccTLD / Tech",
            "registry": "Internet Computer Bureau",
            "official_directory": "https://nic.io/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "The developer and startup standard (.io)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".tech": {
            "category": "gTLD",
            "registry": "Radix Registry",
            "official_directory": "https://nic.tech/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Dedicated domain for technology products (.tech)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".ai": {
            "category": "ccTLD / AI",
            "registry": "Government of Anguilla (.AI Registry)",
            "official_directory": "https://whois.ai/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Premier domain for artificial intelligence (.ai)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
        ".me": {
            "category": "ccTLD / Personal",
            "registry": "doMEn d.o.o.",
            "official_directory": "https://domain.me/",
            "base_registration": 0.00,
            "base_renewal": 0.00,
            "popular": True,
            "description": "Personal branding and portfolio identity (.me)",
            "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
        },
    }

    DEFAULT_TLD_ORDER = [".gy", ".com", ".in", ".org", ".net", ".co", ".io", ".tech", ".ai", ".me"]

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Returns all configured supported extension strings."""
        if hasattr(settings, "SUPPORTED_EXTENSIONS") and settings.SUPPORTED_EXTENSIONS:
            return list(settings.SUPPORTED_EXTENSIONS)
        return list(cls.DEFAULT_TLD_ORDER)

    @classmethod
    def get_catalog_details(cls) -> List[Dict[str, Any]]:
        """Returns detailed extension metadata across supported TLDs."""
        extensions = cls.get_supported_extensions()
        details = []
        for tld in extensions:
            meta = cls.EXTENSIONS_METADATA.get(tld, {
                "category": "gTLD",
                "registry": "Accredited Registry Authority",
                "official_directory": "https://www.icann.org/",
                "base_registration": 0.00,
                "base_renewal": 0.00,
                "popular": False,
                "description": f"Domain extension {tld}",
                "status_notice": "Unverified – Real registrar verification required. Free for application testing.",
            })
            details.append({"extension": tld, **meta})
        return details

    @classmethod
    def is_supported(cls, tld: str) -> bool:
        """Checks if an extension is supported."""
        normalized = tld.lower().strip()
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        return normalized in cls.get_supported_extensions()

    @classmethod
    def get_ordered_extensions(cls, explicit_tld: Optional[str] = None) -> List[str]:
        """
        Returns list of extensions prioritized with the user's requested TLD first.
        """
        all_exts = cls.get_supported_extensions()
        if explicit_tld:
            normalized = explicit_tld.lower().strip()
            if not normalized.startswith("."):
                normalized = f".{normalized}"
            if normalized in all_exts:
                return [normalized] + [e for e in all_exts if e != normalized]
            return [normalized] + all_exts
        return list(all_exts)
