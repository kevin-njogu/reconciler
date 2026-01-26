"""
Pydantic models for authentication and user management.
"""
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

from pydantic import BaseModel, EmailStr, field_validator

from app.auth.config import validate_password_strength


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


# --- Authentication Request/Response Models ---

class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str

    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    must_change_password: bool
    user: "UserResponse"


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


class PasswordResetRequest(BaseModel):
    """Admin password reset request."""
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
    """Request to create a new user (super admin only)."""
    first_name: str
    last_name: str
    email: EmailStr
    password: str
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

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, error = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


class UserUpdateRequest(BaseModel):
    """Request to update a user (admin only)."""
    email: Optional[EmailStr] = None
    role: Optional[UserRoleEnum] = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    status: str
    must_change_password: bool
    created_by_id: Optional[int] = None
    last_login_at: Optional[datetime] = None
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
LoginResponse.model_rebuild()
