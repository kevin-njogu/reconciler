"""
Authentication and Authorization Module.

Provides JWT-based authentication, password hashing, and role-based access control.
"""
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_role,
    require_admin,
    require_super_admin,
)
from app.auth.config import auth_settings

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "require_active_user",
    "require_role",
    "require_admin",
    "require_super_admin",
    "auth_settings",
]
