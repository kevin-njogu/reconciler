"""
Authentication configuration settings.

Loads JWT, password policy, SMTP, OTP, and security settings from environment variables.
All values are required and must be set in the .env file.
"""
import logging
import re

from pydantic_settings import BaseSettings

logger = logging.getLogger("app.auth.config")


class AuthSettings(BaseSettings):
    """Authentication-related settings."""

    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_hours: int

    # Super Admin Creation Secret
    super_admin_secret: str

    # SMTP Email Configuration
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_use_tls: bool

    # Email Domain Restriction
    allowed_email_domain: str

    # OTP Configuration
    otp_login_lifetime_seconds: int
    otp_welcome_lifetime_seconds: int
    otp_forgot_password_lifetime_seconds: int
    otp_max_attempts: int
    otp_resend_cooldown_seconds: int

    # Account Security
    max_failed_login_attempts: int
    account_lockout_minutes: int
    password_expiry_days: int
    password_history_count: int

    # Password Policy
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_digit: bool
    password_require_special: bool

    class Config:
        env_file = ".env"
        extra = "ignore"


auth_settings = AuthSettings()


def validate_auth_config():
    """
    Validate critical auth configuration on startup.

    Raises RuntimeError if required secrets are insecure.
    """
    errors = []

    if len(auth_settings.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")

    if len(auth_settings.super_admin_secret) < 16:
        errors.append("SUPER_ADMIN_SECRET must be at least 16 characters")

    if errors:
        for error in errors:
            logger.critical("Auth configuration error: %s", error)
        raise RuntimeError(
            "Auth configuration validation failed:\n- " + "\n- ".join(errors)
        )


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
