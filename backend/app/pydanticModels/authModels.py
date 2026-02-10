"""
Pydantic models for authentication and user management.

Includes models for 2-step login (credentials + OTP), forgot password,
user management, and audit logging.
"""
from datetime import datetime
from typing import Optional, List, Any, Literal
from enum import Enum

from pydantic import BaseModel, EmailStr, field_validator

from app.auth.config import validate_password_strength, auth_settings


class UserRoleEnum(str, Enum):
    """User roles for API requests."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class UserStatusEnum(str, Enum):
    """User status for API responses."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    DEACTIVATED = "deactivated"


# --- Authentication Request/Response Models (2-Step Login) ---

class LoginRequest(BaseModel):
    """Step 1: Login request with credentials."""
    username: str
    password: str

    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()


class LoginStep1Response(BaseModel):
    """Step 1 response: pre-auth token + OTP metadata."""
    pre_auth_token: str
    otp_sent: bool
    otp_expires_in: int  # seconds
    otp_source: str  # "email" or "welcome_email"
    resend_available_in: int  # seconds until resend is allowed
    message: str


class OTPVerifyRequest(BaseModel):
    """Step 2: Verify OTP code."""
    pre_auth_token: str
    otp_code: str

    @field_validator('otp_code')
    @classmethod
    def otp_code_valid(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('OTP code must be exactly 6 digits')
        return v


class OTPVerifyResponse(BaseModel):
    """Step 2 response: full authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    must_change_password: bool
    user: "UserResponse"


class OTPResendRequest(BaseModel):
    """Request to resend OTP."""
    pre_auth_token: str


class OTPResendResponse(BaseModel):
    """Resend OTP response."""
    otp_sent: bool
    otp_expires_in: int  # seconds
    resend_available_in: int  # seconds
    message: str


# --- Forgot Password Models ---

class ForgotPasswordRequest(BaseModel):
    """Request password reset OTP."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response (intentionally vague for security)."""
    message: str


class VerifyResetOTPRequest(BaseModel):
    """Verify the password reset OTP."""
    email: EmailStr
    otp_code: str

    @field_validator('otp_code')
    @classmethod
    def otp_code_valid(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('OTP code must be exactly 6 digits')
        return v


class VerifyResetOTPResponse(BaseModel):
    """Response with reset token after OTP verification."""
    reset_token: str
    expires_in: int  # seconds


class ResetPasswordRequest(BaseModel):
    """Set new password using reset token."""
    reset_token: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, error = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


class ResetPasswordResponse(BaseModel):
    """Reset password response."""
    message: str


# --- Token Refresh / Logout ---

class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Logout request to revoke refresh token."""
    refresh_token: str


# --- Password Management Models ---

class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, error = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


# --- Super Admin Creation ---

class SuperAdminCreateRequest(BaseModel):
    """Request to create the first super admin user."""
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    secret_key: str

    @field_validator('first_name')
    @classmethod
    def first_name_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('First name cannot be empty')
        if len(v) > 100:
            raise ValueError('First name must be at most 100 characters')
        return v.strip()

    @field_validator('last_name')
    @classmethod
    def last_name_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Last name cannot be empty')
        if len(v) > 100:
            raise ValueError('Last name must be at most 100 characters')
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, error = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


# --- User Management Models ---

class UserCreateRequest(BaseModel):
    """Request to create a new user (super admin only).

    Password is auto-generated by the system and sent via welcome email.
    """
    first_name: str
    last_name: str
    email: EmailStr
    mobile_number: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.USER

    @field_validator('first_name')
    @classmethod
    def first_name_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('First name cannot be empty')
        if len(v) > 100:
            raise ValueError('First name must be at most 100 characters')
        return v.strip()

    @field_validator('last_name')
    @classmethod
    def last_name_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Last name cannot be empty')
        if len(v) > 100:
            raise ValueError('Last name must be at most 100 characters')
        return v.strip()

    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        domain = auth_settings.allowed_email_domain
        if domain:
            email_domain = v.split('@')[1].lower()
            if email_domain != domain.lower():
                raise ValueError(f'Email must be from the {domain} domain')
        return v

    @field_validator('mobile_number')
    @classmethod
    def mobile_number_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Accept E.164 format or basic numeric with optional leading +
        import re
        if not re.match(r'^\+?[1-9]\d{6,14}$', v):
            raise ValueError('Mobile number must be in E.164 format (e.g., +254712345678)')
        return v


class UserCreateResponse(BaseModel):
    """Response after creating a user. Includes one-time initial password."""
    user: "UserResponse"
    initial_password: str
    welcome_email_sent: bool
    message: str


class UserUpdateRequest(BaseModel):
    """Request to update a user (admin only)."""
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    role: Optional[UserRoleEnum] = None

    @field_validator('mobile_number')
    @classmethod
    def mobile_number_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        import re
        if not re.match(r'^\+?[1-9]\d{6,14}$', v):
            raise ValueError('Mobile number must be in E.164 format (e.g., +254712345678)')
        return v


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    role: str
    status: str
    must_change_password: bool
    created_by_id: Optional[int] = None
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response for user list."""
    count: int
    users: List[UserResponse]


# --- Audit Log Models ---

class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_path: Optional[str]
    request_method: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response for audit log list."""
    count: int
    logs: List[AuditLogResponse]


# Update forward references
OTPVerifyResponse.model_rebuild()
UserCreateResponse.model_rebuild()
