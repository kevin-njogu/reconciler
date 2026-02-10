"""
Security utilities for authentication.

Provides password hashing, verification, JWT token operations, and OTP generation.
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.auth.config import auth_settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password string.
    """
    # Bcrypt has a 72-byte limit
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to check against.

    Returns:
        True if password matches, False otherwise.
    """
    try:
        # Bcrypt has a 72-byte limit
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=auth_settings.access_token_expire_minutes
        )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(
        to_encode,
        auth_settings.jwt_secret_key,
        algorithm=auth_settings.jwt_algorithm
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Payload data to encode in the token.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=auth_settings.refresh_token_expire_hours
        )

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(
        to_encode,
        auth_settings.jwt_secret_key,
        algorithm=auth_settings.jwt_algorithm
    )


def create_pre_auth_token(user_id: int, username: str) -> str:
    """
    Create a short-lived pre-auth token issued after credentials verification.

    This token can ONLY be used for OTP verification and resend endpoints.
    It is NOT a valid access token.

    Args:
        user_id: The user's database ID.
        username: The user's username.

    Returns:
        Encoded JWT token string (5-minute expiry).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)

    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "type": "pre_auth"
    }

    return jwt.encode(
        payload,
        auth_settings.jwt_secret_key,
        algorithm=auth_settings.jwt_algorithm
    )


def create_reset_token(user_id: int, email: str) -> str:
    """
    Create a short-lived token for password reset after OTP verification.

    Args:
        user_id: The user's database ID.
        email: The user's email.

    Returns:
        Encoded JWT token string (10-minute expiry).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "type": "password_reset"
    }

    return jwt.encode(
        payload,
        auth_settings.jwt_secret_key,
        algorithm=auth_settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode.

    Returns:
        Decoded token payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_secret_key,
            algorithms=[auth_settings.jwt_algorithm]
        )
        return payload
    except InvalidTokenError:
        return None


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP code.

    Returns:
        6-digit string (zero-padded).
    """
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp_code: str) -> str:
    """
    Hash an OTP code using bcrypt for secure storage.

    Args:
        otp_code: The plain 6-digit OTP.

    Returns:
        Bcrypt hash of the OTP.
    """
    otp_bytes = otp_code.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)  # Slightly fewer rounds for OTPs (short-lived)
    hashed = bcrypt.hashpw(otp_bytes, salt)
    return hashed.decode('utf-8')


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """
    Verify an OTP code against its hash.

    Args:
        plain_otp: The plain OTP code to verify.
        hashed_otp: The bcrypt hash to check against.

    Returns:
        True if OTP matches.
    """
    try:
        otp_bytes = plain_otp.encode('utf-8')
        hashed_bytes = hashed_otp.encode('utf-8')
        return bcrypt.checkpw(otp_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a random password that meets the password policy.

    The generated password will contain uppercase, lowercase, digits,
    and special characters.

    Args:
        length: Password length (minimum 12).

    Returns:
        Random password string.
    """
    if length < 12:
        length = 12

    # Ensure at least one of each required character type
    password_chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*(),.?"),
    ]

    # Fill remaining with mixed characters
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*(),.?"
    for _ in range(length - 4):
        password_chars.append(secrets.choice(all_chars))

    # Shuffle to avoid predictable positions
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)
