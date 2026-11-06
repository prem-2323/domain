from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class DomainAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PREMIUM = "premium"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class ContactInfo(BaseModel):
    """ICANN compliant WHOIS contact details."""
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    organization: Optional[str] = None
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="E.164 phone number format e.g. +1.5551234567")
    address_line_1: str = Field(..., min_length=1)
    address_line_2: Optional[str] = None
    city: str = Field(..., min_length=1)
    state_province: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=1)
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO-3166-1 alpha-2, e.g. US")


class DomainCheckResult(BaseModel):
    """Result of a domain availability lookup."""
    domain: str
    sld: str
    tld: str
    status: DomainAvailabilityStatus
    is_premium: bool = False
    premium_price: Optional[float] = None
    currency: str = "USD"
    provider: str
    is_mock: bool = False


class DomainPriceResult(BaseModel):
    """Result of a domain pricing query."""
    domain: str
    tld: str
    registration_price: float
    renewal_price: float
    transfer_price: Optional[float] = None
    currency: str = "USD"
    discount_percent: Optional[int] = None
    period_years: int = 1
    provider: str
    is_mock: bool = False


class DomainRegisterRequest(BaseModel):
    """Payload to request a domain registration."""
    domain: str
    years: int = Field(default=1, ge=1, le=10)
    registrant_contact: ContactInfo
    admin_contact: Optional[ContactInfo] = None
    tech_contact: Optional[ContactInfo] = None
    billing_contact: Optional[ContactInfo] = None
    whois_privacy: bool = True
    nameservers: Optional[List[str]] = None
    idempotency_key: str = Field(..., description="UUID to prevent duplicate purchases")


class DomainRegisterResult(BaseModel):
    """Outcome of a registration attempt."""
    domain: str
    order_id: str
    transaction_id: str
    is_success: bool
    status: str
    expiration_date: Optional[str] = None
    charged_amount: float
    currency: str = "USD"
    provider: str
    is_mock: bool = False
    message: Optional[str] = None


class DomainRenewRequest(BaseModel):
    """Payload to renew an active domain."""
    domain: str
    years: int = Field(default=1, ge=1, le=9)
    current_expiration_date: Optional[str] = None
    idempotency_key: str


class DomainRenewResult(BaseModel):
    """Outcome of a renewal attempt."""
    domain: str
    order_id: str
    new_expiration_date: str
    charged_amount: float
    is_success: bool
    provider: str
    is_mock: bool = False
    message: Optional[str] = None


class DomainTransferRequest(BaseModel):
    """Payload to initiate an inbound domain transfer."""
    domain: str
    auth_code: str = Field(..., description="EPP transfer authorization key")
    years: int = Field(default=1, ge=1, le=1)
    registrant_contact: ContactInfo
    idempotency_key: str


class DomainTransferResult(BaseModel):
    """Outcome of an inbound transfer initiation."""
    domain: str
    transfer_id: str
    status: str  # e.g. "pending_owner_approval" | "in_progress" | "completed"
    provider: str
    is_mock: bool = False
    message: Optional[str] = None


# ====================================================================
# Exception Hierarchy
# ====================================================================

class RegistrarException(Exception):
    """Base exception for all registrar provider errors."""
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code or "REGISTRAR_ERROR"


class DomainUnavailableError(RegistrarException):
    """Raised when trying to register a domain that is already taken or locked."""
    pass


class RegistrarAuthError(RegistrarException):
    """Raised when registrar API credentials or IP checks fail."""
    pass


class RegistrarQuotaError(RegistrarException):
    """Raised when registrar API rate limits or quota is exceeded."""
    pass


class RegistrarNetworkError(RegistrarException):
    """Raised when communication with upstream registrar times out or disconnects."""
    pass
