from typing import Optional, Dict, Type
from app.services.registrar.base import BaseRegistrarProvider
from app.services.registrar.mock_provider import MockRegistrarProvider
from app.services.registrar.godaddy_provider import GoDaddyRegistrarProvider
from app.services.registrar.namecheap_provider import NamecheapRegistrarProvider
from app.core.config import settings


_PROVIDER_CACHE: Dict[str, BaseRegistrarProvider] = {}


def get_registrar_provider(provider_name: Optional[str] = None) -> BaseRegistrarProvider:
    """
    Factory function returning the active or requested registrar provider instance.
    
    If the requested provider is missing required credentials, automatically falls back
    to MockRegistrarProvider to maintain seamless system stability.
    """
    target = (provider_name or settings.REGISTRAR_PROVIDER or "mock").lower().strip()

    if target in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[target]

    provider_instance: BaseRegistrarProvider

    if target == "godaddy":
        if settings.is_provider_configured("godaddy"):
            provider_instance = GoDaddyRegistrarProvider()
        else:
            # Fall back to mock if credentials not provided
            provider_instance = MockRegistrarProvider()

    elif target == "namecheap":
        if settings.is_provider_configured("namecheap"):
            provider_instance = NamecheapRegistrarProvider()
        else:
            provider_instance = MockRegistrarProvider()

    else:
        # Default is MockRegistrarProvider
        provider_instance = MockRegistrarProvider()

    _PROVIDER_CACHE[target] = provider_instance
    return provider_instance
