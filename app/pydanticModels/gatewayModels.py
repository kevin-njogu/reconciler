"""
Pydantic models for gateway configuration API.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from app.config.gateways import (
    get_valid_country_codes,
    get_valid_currency_codes,
    get_valid_date_formats,
)


class GatewayType(str, Enum):
    """Gateway type enumeration."""
    EXTERNAL = "external"
    INTERNAL = "internal"


class GatewayCreateRequest(BaseModel):
    """Request model for creating a new gateway."""
    name: str = Field(..., min_length=2, max_length=50, description="Unique gateway identifier (lowercase, no spaces)")
    gateway_type: GatewayType = Field(..., description="Gateway type: 'external' or 'internal'")
    display_name: str = Field(..., min_length=2, max_length=100, description="Human-readable gateway name")
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code (e.g., KE, UG)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code (e.g., KES, USD)")
    date_format: str = Field(default="YYYY-MM-DD", description="Expected date format for gateway files")
    charge_keywords: Optional[List[str]] = Field(default=None, description="Keywords to identify charges (external gateways only)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is lowercase and contains only valid characters."""
        v = v.lower().strip()
        if not v.replace("_", "").isalnum():
            raise ValueError("Gateway name must contain only alphanumeric characters and underscores")
        if v.startswith("_") or v.endswith("_"):
            raise ValueError("Gateway name cannot start or end with underscore")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country code against supported countries."""
        v = v.upper().strip()
        valid_codes = get_valid_country_codes()
        if v not in valid_codes:
            raise ValueError(f"Invalid country code. Must be one of: {', '.join(valid_codes)}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code against supported currencies."""
        v = v.upper().strip()
        valid_codes = get_valid_currency_codes()
        if v not in valid_codes:
            raise ValueError(f"Invalid currency code. Must be one of: {', '.join(valid_codes)}")
        return v

    @field_validator("date_format")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format against supported formats."""
        v = v.strip()
        valid_formats = get_valid_date_formats()
        if v not in valid_formats:
            raise ValueError(f"Invalid date format. Must be one of: {', '.join(valid_formats)}")
        return v

    @field_validator("charge_keywords")
    @classmethod
    def validate_charge_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Lowercase all charge keywords for case-insensitive matching."""
        if v is None:
            return None
        return [kw.lower().strip() for kw in v if kw.strip()]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "coop",
                    "gateway_type": "external",
                    "display_name": "Co-operative Bank",
                    "country": "KE",
                    "currency": "KES",
                    "date_format": "YYYY-MM-DD",
                    "charge_keywords": ["charge", "fee", "commission", "ledger fee"]
                }
            ]
        }
    }


class GatewayUpdateRequest(BaseModel):
    """Request model for updating an existing gateway."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Human-readable gateway name")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="ISO 4217 currency code")
    date_format: Optional[str] = Field(None, description="Expected date format for gateway files")
    charge_keywords: Optional[List[str]] = Field(None, description="Keywords to identify charges")
    is_active: Optional[bool] = Field(None, description="Whether the gateway is active")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code against supported countries."""
        if v is None:
            return None
        v = v.upper().strip()
        valid_codes = get_valid_country_codes()
        if v not in valid_codes:
            raise ValueError(f"Invalid country code. Must be one of: {', '.join(valid_codes)}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        """Validate currency code against supported currencies."""
        if v is None:
            return None
        v = v.upper().strip()
        valid_codes = get_valid_currency_codes()
        if v not in valid_codes:
            raise ValueError(f"Invalid currency code. Must be one of: {', '.join(valid_codes)}")
        return v

    @field_validator("date_format")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format against supported formats."""
        if v is None:
            return None
        v = v.strip()
        valid_formats = get_valid_date_formats()
        if v not in valid_formats:
            raise ValueError(f"Invalid date format. Must be one of: {', '.join(valid_formats)}")
        return v

    @field_validator("charge_keywords")
    @classmethod
    def validate_charge_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Lowercase all charge keywords for case-insensitive matching."""
        if v is None:
            return None
        return [kw.lower().strip() for kw in v if kw.strip()]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "display_name": "Co-operative Bank Kenya",
                    "country": "KE",
                    "currency": "KES",
                    "date_format": "DD/MM/YYYY",
                    "charge_keywords": ["charge", "fee", "commission", "ledger fee", "sms alert"],
                    "is_active": True
                }
            ]
        }
    }


class GatewayResponse(BaseModel):
    """Response model for gateway configuration."""
    id: int
    name: str
    gateway_type: str
    display_name: str
    country: str
    currency: str
    date_format: str
    charge_keywords: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GatewayListResponse(BaseModel):
    """Response model for listing gateways."""
    external_gateways: List[GatewayResponse]
    internal_gateways: List[GatewayResponse]
    total_count: int


class GatewayUsageInfo(BaseModel):
    """Response model with gateway usage information."""
    external_gateways: List[str]
    internal_gateways: List[str]
    upload_gateways: dict
    charge_keywords: dict
    usage: dict


# --- Gateway Change Request Models ---

class ChangeRequestType(str, Enum):
    """Type of gateway change request."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"  # Soft delete (deactivate)
    ACTIVATE = "activate"
    PERMANENT_DELETE = "permanent_delete"  # Hard delete from database


class ChangeRequestStatus(str, Enum):
    """Status for gateway change requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GatewayChangeRequestCreate(BaseModel):
    """Request model for creating a gateway change request."""
    request_type: ChangeRequestType
    gateway_name: str = Field(..., min_length=2, max_length=50)
    proposed_changes: dict = Field(..., description="Proposed gateway configuration")

    @field_validator("gateway_name")
    @classmethod
    def validate_gateway_name(cls, v: str) -> str:
        """Ensure name is lowercase and contains only valid characters."""
        v = v.lower().strip()
        if not v.replace("_", "").isalnum():
            raise ValueError("Gateway name must contain only alphanumeric characters and underscores")
        return v


class GatewayChangeRequestReview(BaseModel):
    """Request model for approving/rejecting a change request."""
    approved: bool
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection (required if rejecting)")

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        """Require rejection reason if not approved."""
        # Access other field values through info.data
        approved = info.data.get("approved", True)
        if not approved and (not v or not v.strip()):
            raise ValueError("Rejection reason is required when rejecting a request")
        return v.strip() if v else None


class GatewayChangeRequestResponse(BaseModel):
    """Response model for gateway change requests."""
    id: int
    request_type: str
    status: str
    gateway_id: Optional[int]
    gateway_name: str
    proposed_changes: dict
    requested_by_id: int
    requested_by_name: Optional[str] = None
    created_at: datetime
    reviewed_by_id: Optional[int]
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}


class GatewayChangeRequestListResponse(BaseModel):
    """Response model for listing gateway change requests."""
    count: int
    requests: List[GatewayChangeRequestResponse]


# --- Gateway Options Models ---

class CountryOption(BaseModel):
    """Country option for dropdown."""
    code: str
    name: str


class CurrencyOption(BaseModel):
    """Currency option for dropdown."""
    code: str
    name: str


class DateFormatOption(BaseModel):
    """Date format option for dropdown."""
    format: str
    example: str


class GatewayOptionsResponse(BaseModel):
    """Response model for gateway configuration options."""
    countries: List[CountryOption]
    currencies: List[CurrencyOption]
    date_formats: List[DateFormatOption]
