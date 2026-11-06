from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class RegistrationRequestStatus(str, Enum):
    PENDING = "pending"
    VERIFICATION_REQUIRED = "verification_required"
    VERIFIED_AVAILABLE = "verified_available"
    UNAVAILABLE = "unavailable"
    REGISTRATION_IN_PROGRESS = "registration_in_progress"
    REGISTERED = "registered"
    REJECTED = "rejected"


STATUS_LABELS = {
    RegistrationRequestStatus.PENDING: "Pending Initial Review",
    RegistrationRequestStatus.VERIFICATION_REQUIRED: "Verification Required (.GY Registry)",
    RegistrationRequestStatus.VERIFIED_AVAILABLE: "Verified Available by Registrar",
    RegistrationRequestStatus.UNAVAILABLE: "Unavailable / Reserved by .GY Registry",
    RegistrationRequestStatus.REGISTRATION_IN_PROGRESS: "Registration in Progress with Partner",
    RegistrationRequestStatus.REGISTERED: "Registration Manually Confirmed",
    RegistrationRequestStatus.REJECTED: "Request Rejected",
}


# --- Customer Submission Models ---

class CreateRegistrationRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=120, description="Full customer name")
    customer_email: str = Field(..., min_length=5, max_length=255, description="Customer email address")
    domain: str = Field(..., min_length=4, max_length=100, description="Requested domain ending in .gy (e.g. tala.gy)")
    message: Optional[str] = Field(default=None, max_length=1000, description="Optional customer message or intended use")


class CustomerRequestCreatedResponse(BaseModel):
    request_id: str = Field(..., description="Unique cryptographically secure Request ID (>=128 bits entropy)")
    tracking_token: str = Field(..., description="Private customer tracking token for checking personal submission")
    domain: str = Field(..., description="Requested domain name")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email address")
    status: RegistrationRequestStatus = Field(default=RegistrationRequestStatus.PENDING)
    status_label: str = Field(..., description="Human-readable status label")
    estimated_annual_price: float = Field(default=45.0, description="Estimated price from .GY accredited registrar (~$45.00/yr)")
    pricing_status: str = Field(default="estimated", description="'estimated' | 'confirmed'")
    currency: str = Field(default="USD")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    disclaimer: str = Field(
        default="Submitting a request does NOT register, hold, or reserve the domain name. Allocation requires verification by the University of Guyana .GY Registry and accredited registrars."
    )


# --- Public Sanitized Tracking Model (Zero Private Data) ---

class PublicRegistrationRequestResponse(BaseModel):
    """
    Sanitized tracking response for public lookups.
    Strictly contains NO customer email, NO customer message, and NO internal admin notes.
    """
    request_id: str = Field(..., description="Unique request identifier")
    domain: str = Field(..., description="Requested domain name")
    status: RegistrationRequestStatus = Field(..., description="Current request status")
    status_label: str = Field(..., description="Human-readable status label")
    pricing_type: str = Field(default="estimated", description="'estimated' | 'confirmed'")
    pricing_amount: float = Field(default=45.0, description="Estimated rate (~$45.00) or administrator-confirmed quote")
    currency: str = Field(default="USD")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")
    disclaimer: str = Field(
        default="Submitting a request does NOT register, hold, or reserve the domain name. Final allocation requires verification by the University of Guyana .GY Registry and accredited registrars."
    )


# --- Customer Token-Verified Response Model ---

class CustomerVerifiedRequestResponse(BaseModel):
    """
    Extended response visible only to the customer holding the private tracking token.
    Still excludes internal admin notes and private registrar liaison comments.
    """
    request_id: str
    domain: str
    customer_name: str
    customer_email: str
    message: Optional[str] = None
    status: RegistrationRequestStatus
    status_label: str
    estimated_annual_price: float
    confirmed_price: Optional[float] = None
    pricing_type: str = "estimated"
    currency: str = "USD"
    created_at: str
    updated_at: str
    disclaimer: str


# --- Admin Protected Models ---

class UpdateRegistrationRequest(BaseModel):
    status: Optional[RegistrationRequestStatus] = Field(default=None, description="Updated request status")
    admin_notes: Optional[str] = Field(default=None, max_length=2000, description="Internal admin notes")
    confirmed_price: Optional[float] = Field(default=None, ge=0.0, description="Confirmed pricing from accredited registrar")
    confirmation_reference: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Official registrar allocation receipt/reference (Required when status is 'registered')",
    )


class AdminRegistrationRequestResponse(BaseModel):
    """
    Full administrative response model for authenticated administrators only.
    Customer tracking tokens are strictly excluded to protect confidentiality.
    """
    request_id: str
    domain: str
    customer_name: str
    customer_email: str
    message: Optional[str] = None
    status: RegistrationRequestStatus
    status_label: str
    estimated_annual_price: float
    confirmed_price: Optional[float] = None
    pricing_type: str = "estimated"
    currency: str = "USD"
    admin_notes: Optional[str] = None
    confirmation_reference: Optional[str] = None
    created_at: str
    updated_at: str
    disclaimer: str


class AdminRegistrationRequestListResponse(BaseModel):
    total: int = Field(..., description="Total count of registration requests")
    requests: List[AdminRegistrationRequestResponse] = Field(..., description="List of registration requests")


# --- Admin Session & Login Models ---

class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="Admin username")
    password: str = Field(..., min_length=1, max_length=128, description="Admin password")


class AdminLoginResponse(BaseModel):
    session_token: str
    username: str
    expires_at: str
    message: str = "Admin authenticated successfully."
