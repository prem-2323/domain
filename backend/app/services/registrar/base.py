from abc import ABC, abstractmethod
from typing import List
from app.models.registrar import (
    DomainCheckResult,
    DomainPriceResult,
    DomainRegisterRequest,
    DomainRegisterResult,
    DomainRenewRequest,
    DomainRenewResult,
    DomainTransferRequest,
    DomainTransferResult,
)


class BaseRegistrarProvider(ABC):
    """
    Abstract interface for Domain Registrar Providers.
    All concrete registrar integrations (Mock, GoDaddy, Namecheap, etc.) must implement this interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the registrar provider (e.g. 'mock', 'godaddy', 'namecheap')."""
        pass

    @property
    @abstractmethod
    def is_sandbox(self) -> bool:
        """Returns True if the provider is currently operating in a sandbox or test environment."""
        pass

    @abstractmethod
    async def check_availability(self, domain: str) -> DomainCheckResult:
        """
        Queries registrar for availability status of a single domain name.
        Returns a standardized DomainCheckResult.
        """
        pass

    @abstractmethod
    async def check_bulk_availability(self, domains: List[str]) -> List[DomainCheckResult]:
        """
        Queries registrar for availability across multiple domains concurrently.
        """
        pass

    @abstractmethod
    async def get_pricing(self, domain: str, tld: str) -> DomainPriceResult:
        """
        Queries registrar for live registration and renewal pricing.
        """
        pass

    @abstractmethod
    async def register_domain(self, request: DomainRegisterRequest) -> DomainRegisterResult:
        """
        Registers a domain name with the registrar.
        NOTE: Must use idempotency key and safe error handling.
        """
        pass

    @abstractmethod
    async def renew_domain(self, request: DomainRenewRequest) -> DomainRenewResult:
        """
        Renews an existing registered domain for a specified number of years.
        """
        pass

    @abstractmethod
    async def transfer_domain(self, request: DomainTransferRequest) -> DomainTransferResult:
        """
        Initiates an inbound domain transfer with the registrar using an EPP auth code.
        """
        pass
