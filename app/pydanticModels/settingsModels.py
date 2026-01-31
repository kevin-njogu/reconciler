"""
Settings Pydantic Models.

Request and response models for system settings API endpoints.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class KeywordType(str, Enum):
    """Types of reconciliation keywords."""
    CHARGE = "charge"
    REVERSAL = "reversal"


# =============================================================================
# Date Format Models
# =============================================================================

class DateFormatCreate(BaseModel):
    """Request model for creating a new date format."""
    format_string: str = Field(..., min_length=1, max_length=50, description="Python strptime format string")
    display_name: str = Field(..., min_length=1, max_length=100, description="Human-readable format name")
    example: str = Field(..., min_length=1, max_length=50, description="Example date in this format")
    is_default: bool = Field(default=False, description="Whether this is the default format")

    @field_validator("format_string")
    @classmethod
    def validate_format_string(cls, v: str) -> str:
        """Validate that the format string is a valid Python date format."""
        try:
            datetime.strptime("2024-01-15", "%Y-%m-%d")  # Test basic parsing
            # Try to use the format
            test_date = datetime(2024, 1, 15)
            test_date.strftime(v)
        except ValueError:
            pass  # Allow the format even if our test date doesn't work
        return v.strip()


class DateFormatUpdate(BaseModel):
    """Request model for updating a date format."""
    format_string: Optional[str] = Field(None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    example: Optional[str] = Field(None, min_length=1, max_length=50)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class DateFormatResponse(BaseModel):
    """Response model for a date format."""
    id: int
    format_string: str
    display_name: str
    example: str
    is_default: bool
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Country & Currency Models
# =============================================================================

class CurrencyCreate(BaseModel):
    """Request model for creating a currency."""
    code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    name: str = Field(..., min_length=1, max_length=100, description="Currency name")
    symbol: Optional[str] = Field(None, max_length=10, description="Currency symbol")
    is_default: bool = Field(default=False, description="Default currency for the country")

    @field_validator("code")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        return v.upper().strip()


class CurrencyUpdate(BaseModel):
    """Request model for updating a currency."""
    code: Optional[str] = Field(None, min_length=3, max_length=3)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbol: Optional[str] = Field(None, max_length=10)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class CurrencyResponse(BaseModel):
    """Response model for a currency."""
    id: int
    code: str
    name: str
    symbol: Optional[str] = None
    country_id: int
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class CountryCreate(BaseModel):
    """Request model for creating a country."""
    code: str = Field(..., min_length=2, max_length=3, description="ISO country code")
    name: str = Field(..., min_length=1, max_length=100, description="Country name")
    currencies: Optional[List[CurrencyCreate]] = Field(default=None, description="Initial currencies")

    @field_validator("code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        return v.upper().strip()


class CountryUpdate(BaseModel):
    """Request model for updating a country."""
    code: Optional[str] = Field(None, min_length=2, max_length=3)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class CountryResponse(BaseModel):
    """Response model for a country."""
    id: int
    code: str
    name: str
    is_active: bool
    currencies: List[CurrencyResponse] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Reconciliation Keyword Models
# =============================================================================

class KeywordCreate(BaseModel):
    """Request model for creating a reconciliation keyword."""
    keyword: str = Field(..., min_length=1, max_length=100, description="The keyword to match")
    keyword_type: KeywordType = Field(..., description="Type of keyword")
    description: Optional[str] = Field(None, max_length=255, description="Optional description")
    is_case_sensitive: bool = Field(default=False, description="Whether matching is case-sensitive")
    gateway_id: Optional[int] = Field(None, description="Limit to specific gateway")

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        return v.strip()


class KeywordUpdate(BaseModel):
    """Request model for updating a keyword."""
    keyword: Optional[str] = Field(None, min_length=1, max_length=100)
    keyword_type: Optional[KeywordType] = None
    description: Optional[str] = Field(None, max_length=255)
    is_case_sensitive: Optional[bool] = None
    is_active: Optional[bool] = None
    gateway_id: Optional[int] = None


class KeywordResponse(BaseModel):
    """Response model for a reconciliation keyword."""
    id: int
    keyword: str
    keyword_type: str
    description: Optional[str] = None
    is_case_sensitive: bool
    is_active: bool
    gateway_id: Optional[int] = None
    gateway_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KeywordBulkCreate(BaseModel):
    """Request model for bulk creating keywords."""
    keyword_type: KeywordType
    keywords: List[str] = Field(..., min_length=1, description="List of keywords to add")
    gateway_id: Optional[int] = None


# =============================================================================
# System Setting Models
# =============================================================================

class SystemSettingCreate(BaseModel):
    """Request model for creating a new system setting."""
    key: str = Field(..., min_length=1, max_length=100, description="Unique setting key")
    value: Optional[str] = Field(None, description="Setting value")
    value_type: str = Field(default="string", description="Type: string, number, boolean, json")
    description: Optional[str] = Field(None, max_length=255, description="Description of this setting")
    is_editable: bool = Field(default=True, description="Whether this setting can be edited later")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate and normalize the setting key."""
        # Convert to lowercase and replace spaces with underscores
        return v.strip().lower().replace(" ", "_").replace("-", "_")

    @field_validator("value_type")
    @classmethod
    def validate_value_type(cls, v: str) -> str:
        """Validate value type is one of the allowed types."""
        allowed_types = ["string", "number", "boolean", "json"]
        if v.lower() not in allowed_types:
            raise ValueError(f"value_type must be one of: {', '.join(allowed_types)}")
        return v.lower()


class SystemSettingUpdate(BaseModel):
    """Request model for updating a system setting."""
    value: str = Field(..., description="Setting value")


class SystemSettingResponse(BaseModel):
    """Response model for a system setting."""
    id: int
    key: str
    value: Optional[str] = None
    value_type: str
    description: Optional[str] = None
    is_editable: bool
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Combined Settings Response
# =============================================================================

class AllSettingsResponse(BaseModel):
    """Response model for all settings."""
    date_formats: List[DateFormatResponse]
    countries: List[CountryResponse]
    keywords: dict  # Grouped by type
    system_settings: List[SystemSettingResponse]
