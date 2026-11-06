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


class CreateRegistrationRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=120, description="Full customer name")
    customer_email: str = Field(..., min_length=5, max_length=255, description="Customer email address")
    domain: str = Field(..., min_length=4, max_length=100, description="Requested domain ending in .gy (e.g. tala.gy)")
    message: Optional[str] = Field(default=None, max_length=1000, description="Optional customer message or intended use")


class UpdateRegistrationRequest(BaseModel):
    status: Optional[RegistrationRequestStatus] = Field(default=None, description="Updated request status")
    admin_notes: Optional[str] = Field(default=None, max_length=2000, description="Internal admin notes")
    confirmed_price: Optional[float] = Field(default=None, ge=0.0, description="Confirmed pricing from accredited registrar")


class RegistrationRequestResponse(BaseModel):
    request_id: str = Field(..., description="Unique request identifier (e.g. REQ-GY-7F8A2D1C)")
    domain: str = Field(..., description="Requested domain name (e.g. tala.gy)")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email address")
    message: Optional[str] = Field(default=None, description="Optional customer message")
    status: RegistrationRequestStatus = Field(default=RegistrationRequestStatus.PENDING)
    status_label: str = Field(..., description="Human-readable status label")
    estimated_annual_price: float = Field(default=45.0, description="Estimated price from .GY accredited registrar (~$45.00/yr)")
    confirmed_price: Optional[float] = Field(default=None, description="Confirmed pricing once verified with registrar")
    currency: str = Field(default="USD")
    admin_notes: Optional[str] = Field(default=None, description="Internal notes added by admin")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC update timestamp")
    disclaimer: str = Field(
        default="Submitting a request does NOT register, hold, or reserve the domain name. Final allocation requires verification by the University of Guyana .GY Registry and accredited registrars."
    )


class RegistrationRequestListResponse(BaseModel):
    total: int = Field(..., description="Total count of registration requests")
    requests: List[RegistrationRequestResponse] = Field(..., description="List of registration requests")
