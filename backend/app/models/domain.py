from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class DomainAvailability(str, Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    PREMIUM = "premium"
    UNVERIFIED = "unverified"


class PricingModel(BaseModel):
    registration_price: float = Field(..., description="Annual registration price in USD")
    renewal_price: float = Field(..., description="Annual renewal price in USD")
    currency: str = Field(default="USD", description="Currency code")
    discount_percent: Optional[int] = Field(default=None, description="Discount percentage if applicable")
    period_years: int = Field(default=1, description="Registration period in years")
    is_mock: bool = Field(default=True, description="Flag indicating estimate/unverified rate")
    pricing_note: str = Field(
        default="Official .GY accredited registrar estimated rate. Final price confirmed upon registrar checkout.",
        description="Transparent pricing notice"
    )


class DomainResult(BaseModel):
    domain: str = Field(..., description="Full .gy domain name (e.g. tala.gy)")
    name: str = Field(..., description="Second level domain name without extension (e.g. tala)")
    extension: str = Field(default=".gy", description="TLD extension (exclusively .gy)")
    availability: DomainAvailability = Field(..., description="Availability status: available, taken, premium, unverified")
    price: PricingModel = Field(..., description="Pricing breakdown")
    is_exact_match: bool = Field(default=False, description="Whether this is the exact domain requested")
    status_label: str = Field(
        default="Unverified – Real Registrar Check Required",
        description="Explicit human-readable status"
    )
    registry: str = Field(
        default="University of Guyana .GY Registry",
        description="Official registry authority"
    )
    features: List[str] = Field(
        default_factory=lambda: [
            "Official .GY Country-Code TLD",
            "Cloudflare DNS Management",
            "1-Click Vercel & Render DNS Sync",
            "Accredited Registrar Fulfillment",
        ],
        description="Standard inclusions for this domain"
    )
    is_mock: bool = Field(default=True, description="Flag indicating estimate before live registrar checkout")


class DomainSearchResponse(BaseModel):
    query: str = Field(..., description="Original search input")
    normalized_name: str = Field(..., description="Sanitized second level domain name")
    extension: str = Field(default=".gy", description="Domain extension (exclusively .gy)")
    registry: str = Field(default="University of Guyana .GY Registry", description="Registry authority")
    official_registrars_url: str = Field(
        default="https://registry.gy/registrars/",
        description="Official directory of accredited .gy registrars"
    )
    is_valid: bool = Field(default=True, description="Whether domain name is syntactically valid")
    exact_match: Optional[DomainResult] = Field(default=None, description="Exact match result (e.g. tala.gy)")
    suggestions: List[DomainResult] = Field(default_factory=list, description="Alternative .gy variations")
    total_results: int = Field(..., description="Total .gy variations returned")
    is_mock: bool = Field(default=True, description="Flag indicating simulated preview")
    disclaimer: str = Field(
        default="MasterTools Domains operates exclusively with the .gy ccTLD. Availability is unverified until confirmed with an accredited .GY registrar. No fake registrations are performed.",
        description="Accreditation & verification disclaimer"
    )
