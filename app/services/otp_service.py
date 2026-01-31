"""
OTP (One-Time Password) lifecycle service.

Handles OTP creation, verification, resend cooldown, and cleanup.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.auth.config import auth_settings
from app.auth.security import generate_otp, hash_otp, verify_otp
from app.sqlModels.authEntities import OTPToken, OTPPurpose


class OTPService:
    """Manages OTP lifecycle: creation, verification, resend, cleanup."""

    @staticmethod
    def get_lifetime_seconds(purpose: str) -> int:
        """Get OTP lifetime in seconds based on purpose."""
        if purpose == OTPPurpose.LOGIN.value:
            return auth_settings.otp_login_lifetime_seconds
        elif purpose == OTPPurpose.WELCOME.value:
            return auth_settings.otp_welcome_lifetime_seconds
        elif purpose == OTPPurpose.FORGOT_PASSWORD.value:
            return auth_settings.otp_forgot_password_lifetime_seconds
        return auth_settings.otp_login_lifetime_seconds

    @staticmethod
    def create_otp(
        db: Session,
        user_id: int,
        purpose: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, OTPToken]:
        """
        Create a new OTP for the given user and purpose.

        Invalidates any existing unused OTPs for the same user+purpose.

        Args:
            db: Database session.
            user_id: Target user ID.
            purpose: OTP purpose (login, welcome, forgot_password).
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            Tuple of (plain_otp_code, otp_record).
        """
        # Invalidate existing unused OTPs for this user+purpose
        db.query(OTPToken).filter(
            OTPToken.user_id == user_id,
            OTPToken.purpose == purpose,
            OTPToken.is_used == False,
        ).update({"is_used": True, "used_at": datetime.now(timezone.utc)})

        # Generate and hash new OTP
        plain_otp = generate_otp()
        otp_hash_value = hash_otp(plain_otp)

        # Calculate expiry
        lifetime = OTPService.get_lifetime_seconds(purpose)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=lifetime)

        # Create OTP record
        otp_record = OTPToken(
            user_id=user_id,
            otp_hash=otp_hash_value,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(otp_record)
        db.flush()

        return plain_otp, otp_record

    @staticmethod
    def verify(
        db: Session,
        user_id: int,
        otp_code: str,
        purpose: str,
    ) -> Tuple[bool, str]:
        """
        Verify an OTP code for the given user and purpose.

        Args:
            db: Database session.
            user_id: The user's ID.
            otp_code: The plain OTP code to verify.
            purpose: Expected OTP purpose.

        Returns:
            Tuple of (success, error_message).
        """
        # Find the latest non-used OTP for this user+purpose
        otp_record = (
            db.query(OTPToken)
            .filter(
                OTPToken.user_id == user_id,
                OTPToken.purpose == purpose,
                OTPToken.is_used == False,
            )
            .order_by(OTPToken.created_at.desc())
            .first()
        )

        if not otp_record:
            return False, "No valid OTP found. Please request a new code."

        # Check expiry
        if otp_record.is_expired():
            return False, "OTP has expired. Please request a new code."

        # Check max attempts
        if otp_record.attempts >= auth_settings.otp_max_attempts:
            return False, "Too many failed attempts. Please request a new code."

        # Verify the OTP hash
        if not verify_otp(otp_code, otp_record.otp_hash):
            otp_record.attempts += 1
            db.flush()
            remaining = auth_settings.otp_max_attempts - otp_record.attempts
            if remaining <= 0:
                return False, "Too many failed attempts. Please request a new code."
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

        # Mark as used
        otp_record.is_used = True
        otp_record.used_at = datetime.now(timezone.utc)
        db.flush()

        return True, ""

    @staticmethod
    def find_valid_otp(
        db: Session,
        user_id: int,
        purpose: str,
    ) -> Optional[OTPToken]:
        """
        Find an existing valid (non-expired, non-used) OTP for user+purpose.

        Used to check if a welcome OTP is still active before sending a new one.

        Args:
            db: Database session.
            user_id: The user's ID.
            purpose: OTP purpose.

        Returns:
            OTPToken if a valid one exists, None otherwise.
        """
        otp_record = (
            db.query(OTPToken)
            .filter(
                OTPToken.user_id == user_id,
                OTPToken.purpose == purpose,
                OTPToken.is_used == False,
            )
            .order_by(OTPToken.created_at.desc())
            .first()
        )

        if otp_record and not otp_record.is_expired():
            return otp_record
        return None

    @staticmethod
    def can_resend(
        db: Session,
        user_id: int,
        purpose: str,
    ) -> Tuple[bool, int]:
        """
        Check if the resend cooldown has passed.

        Args:
            db: Database session.
            user_id: The user's ID.
            purpose: OTP purpose.

        Returns:
            Tuple of (can_resend, seconds_remaining).
        """
        latest_otp = (
            db.query(OTPToken)
            .filter(
                OTPToken.user_id == user_id,
                OTPToken.purpose == purpose,
            )
            .order_by(OTPToken.created_at.desc())
            .first()
        )

        if not latest_otp:
            return True, 0

        created = latest_otp.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        cooldown = timedelta(seconds=auth_settings.otp_resend_cooldown_seconds)
        next_allowed = created + cooldown
        now = datetime.now(timezone.utc)

        if now >= next_allowed:
            return True, 0

        remaining = int((next_allowed - now).total_seconds())
        return False, remaining

    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """
        Delete OTP records older than 24 hours.

        Args:
            db: Database session.

        Returns:
            Number of records deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        count = (
            db.query(OTPToken)
            .filter(OTPToken.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.flush()
        return count
