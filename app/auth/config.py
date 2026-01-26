"""
Authentication configuration settings.

Loads JWT and password policy settings from environment variables.
"""
import os
import re
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class AuthSettings(BaseSettings):
    """Authentication-related settings."""

    # JWT Configuration
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "change-this-in-production-min-32-chars-secret-key"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    refresh_token_expire_days: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # Super Admin Creation Secret
    super_admin_secret: str = os.getenv(
        "SUPER_ADMIN_SECRET",
        "super-admin-creation-secret-change-this"
    )

    # Password Policy
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


auth_settings = AuthSettings()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password against security policy.

    Args:
        password: The password to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if len(password) < auth_settings.password_min_length:
        return False, f"Password must be at least {auth_settings.password_min_length} characters"

    if auth_settings.password_require_uppercase and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if auth_settings.password_require_lowercase and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if auth_settings.password_require_digit and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if auth_settings.password_require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    return True, ""
