"""
Pydantic models for gateway configuration API.

Unified gateway models only (legacy GatewayConfig removed).
"""
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class FileConfigType(str, Enum):
    """Type of file configuration."""
    EXTERNAL = "external"
    INTERNAL = "internal"


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


# =============================================================================
# Gateway File Config Models
# =============================================================================

class GatewayFileConfigCreate(BaseModel):
    """Request model for creating a gateway file configuration."""
    config_type: FileConfigType = Field(..., description="Configuration type: 'external' or 'internal'")
    name: str = Field(..., min_length=2, max_length=50, description="Unique config name (e.g., 'equity' or 'workpay_equity')")
    expected_filetypes: List[str] = Field(default=["xlsx", "xls", "csv"], description="List of expected file types")
    header_row_config: Dict[str, int] = Field(default_factory=lambda: {"xlsx": 0, "xls": 0, "csv": 0},
                                               description="Rows to skip per filetype")
    end_of_data_signal: Optional[str] = Field(None, max_length=255, description="Text that signals end of data")
    date_format: Optional[str] = Field(None, max_length=50, description="Python strftime format string (e.g., '%d/%m/%Y')")
    charge_keywords: Optional[List[str]] = Field(None, description="Keywords to identify charges (external only)")
    column_mapping: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Mapping from template columns to possible raw column names"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.lower().strip()
        if not v.replace("_", "").isalnum():
            raise ValueError("Config name must contain only alphanumeric characters and underscores")
        if v.startswith("_") or v.endswith("_"):
            raise ValueError("Config name cannot start or end with underscore")
        return v

    @field_validator("expected_filetypes")
    @classmethod
    def validate_filetypes(cls, v: List[str]) -> List[str]:
        valid_types = {"xlsx", "xls", "csv"}
        for ft in v:
            if ft.lower() not in valid_types:
                raise ValueError(f"Invalid filetype '{ft}'. Must be one of: {', '.join(valid_types)}")
        return [ft.lower() for ft in v]

    @field_validator("charge_keywords")
    @classmethod
    def validate_charge_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [kw.lower().strip() for kw in v if kw.strip()]

    @model_validator(mode='after')
    def validate_internal_naming(self):
        if self.config_type == FileConfigType.INTERNAL:
            if not self.name.startswith("workpay_"):
                raise ValueError("Internal gateway name must start with 'workpay_'")
        else:
            if self.name.startswith("workpay_"):
                raise ValueError("External gateway name cannot start with 'workpay_'")
        return self


class GatewayFileConfigUpdate(BaseModel):
    """Request model for updating a gateway file configuration."""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    expected_filetypes: Optional[List[str]] = None
    header_row_config: Optional[Dict[str, int]] = None
    end_of_data_signal: Optional[str] = Field(None, max_length=255)
    date_format: Optional[str] = Field(None, max_length=50, description="Python strftime format string")
    charge_keywords: Optional[List[str]] = None
    column_mapping: Optional[Dict[str, List[str]]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.lower().strip()
        if not v.replace("_", "").isalnum():
            raise ValueError("Config name must contain only alphanumeric characters and underscores")
        return v

    @field_validator("expected_filetypes")
    @classmethod
    def validate_filetypes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        valid_types = {"xlsx", "xls", "csv"}
        for ft in v:
            if ft.lower() not in valid_types:
                raise ValueError(f"Invalid filetype '{ft}'. Must be one of: {', '.join(valid_types)}")
        return [ft.lower() for ft in v]

    @field_validator("charge_keywords")
    @classmethod
    def validate_charge_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [kw.lower().strip() for kw in v if kw.strip()]


class GatewayFileConfigResponse(BaseModel):
    """Response model for a gateway file configuration."""
    id: int
    gateway_id: int
    config_type: str
    name: str
    expected_filetypes: List[str] = []
    header_row_config: Dict[str, int] = {}
    end_of_data_signal: Optional[str] = None
    date_format: Optional[str] = None
    charge_keywords: List[str] = []
    column_mapping: Optional[Dict[str, List[str]]] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


# =============================================================================
# Unified Gateway Models
# =============================================================================

class UnifiedGatewayCreate(BaseModel):
    """Request model for creating a unified gateway with both configs."""
    display_name: str = Field(..., min_length=2, max_length=100, description="Human-readable gateway name")
    description: Optional[str] = Field(None, description="Optional gateway description")
    country: Optional[str] = Field(None, max_length=100, description="Country name (e.g., Kenya, Uganda)")
    currency_code: Optional[str] = Field(None, max_length=3, description="ISO 4217 currency code (e.g., KES, USD)")
    external_config: GatewayFileConfigCreate = Field(..., description="External file configuration")
    internal_config: GatewayFileConfigCreate = Field(..., description="Internal file configuration")

    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.upper().strip()

    @model_validator(mode='after')
    def validate_config_types(self):
        if self.external_config.config_type != FileConfigType.EXTERNAL:
            raise ValueError("External config must have config_type 'external'")
        if self.internal_config.config_type != FileConfigType.INTERNAL:
            raise ValueError("Internal config must have config_type 'internal'")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "display_name": "Equity Bank",
                    "description": "Equity Bank Kenya gateway",
                    "country": "Kenya",
                    "currency_code": "KES",
                    "external_config": {
                        "config_type": "external",
                        "name": "equity",
                        "expected_filetypes": ["xlsx", "xls"],
                        "header_row_config": {"xlsx": 5, "xls": 5, "csv": 0},
                        "date_format": "%d/%m/%Y",
                        "charge_keywords": ["charge", "fee", "commission"]
                    },
                    "internal_config": {
                        "config_type": "internal",
                        "name": "workpay_equity",
                        "expected_filetypes": ["xlsx", "csv"],
                        "date_format": "%Y-%m-%d"
                    }
                }
            ]
        }
    }


class UnifiedGatewayUpdate(BaseModel):
    """Request model for updating a unified gateway."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    country: Optional[str] = Field(None, max_length=100)
    currency_code: Optional[str] = Field(None, max_length=3)
    external_config: Optional[GatewayFileConfigUpdate] = None
    internal_config: Optional[GatewayFileConfigUpdate] = None
    is_active: Optional[bool] = None

    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.upper().strip()


class UnifiedGatewayResponse(BaseModel):
    """Response model for a unified gateway."""
    id: int
    display_name: str
    description: Optional[str] = None
    country: Optional[str] = None
    currency_code: Optional[str] = None
    is_active: bool = True
    external_config: Optional[GatewayFileConfigResponse] = None
    internal_config: Optional[GatewayFileConfigResponse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UnifiedGatewayListResponse(BaseModel):
    """Response model for listing unified gateways."""
    gateways: List[UnifiedGatewayResponse]
    total_count: int


# =============================================================================
# Change Request Models
# =============================================================================

class UnifiedGatewayChangeRequestCreate(BaseModel):
    """Request model for creating a unified gateway change request."""
    request_type: ChangeRequestType
    display_name: str = Field(..., min_length=2, max_length=100, description="Gateway display name")
    proposed_changes: dict = Field(..., description="Proposed unified gateway configuration")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_type": "create",
                    "display_name": "Equity Bank",
                    "proposed_changes": {
                        "display_name": "Equity Bank",
                        "description": "Equity Bank Kenya gateway",
                        "country": "Kenya",
                        "currency_code": "KES",
                        "external_config": {
                            "config_type": "external",
                            "name": "equity",
                            "date_format": "%d/%m/%Y",
                            "charge_keywords": ["charge", "fee"]
                        },
                        "internal_config": {
                            "config_type": "internal",
                            "name": "workpay_equity",
                            "date_format": "%Y-%m-%d"
                        }
                    }
                }
            ]
        }
    }


class GatewayChangeRequestReview(BaseModel):
    """Request model for approving/rejecting a change request."""
    approved: bool
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection (required if rejecting)")

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        approved = info.data.get("approved", True)
        if not approved and (not v or not v.strip()):
            raise ValueError("Rejection reason is required when rejecting a request")
        return v.strip() if v else None


class GatewayChangeRequestResponse(BaseModel):
    """Response model for gateway change requests."""
    id: int
    request_type: str
    status: str
    unified_gateway_id: Optional[int] = None
    gateway_display_name: Optional[str] = None
    proposed_changes: dict
    requested_by_id: int
    requested_by_name: Optional[str] = None
    created_at: datetime
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class GatewayChangeRequestListResponse(BaseModel):
    """Response model for listing gateway change requests."""
    count: int
    requests: List[GatewayChangeRequestResponse]
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
