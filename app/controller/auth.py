"""
Authentication API Endpoints.

Provides 2-step login (credentials + OTP), token refresh, logout,
forgot password (OTP-based), and password management.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database
from app.middleware.security import limiter

logger = logging.getLogger("app.auth")
from app.auth.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    create_pre_auth_token,
    create_reset_token,
    decode_token,
    verify_otp as verify_otp_hash,
)
from app.auth.config import auth_settings, validate_password_strength
from app.auth.dependencies import get_current_user, get_pre_auth_user
from app.sqlModels.authEntities import (
    User, RefreshToken, LoginSession, UserStatus, AuditLog, OTPPurpose,
)
from app.services.otp_service import OTPService
from app.services.email_service import EmailService
from app.pydanticModels.authModels import (
    LoginRequest,
    LoginStep1Response,
    OTPVerifyRequest,
    OTPVerifyResponse,
    OTPResendRequest,
    OTPResendResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyResetOTPRequest,
    VerifyResetOTPResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    LogoutRequest,
    PasswordChangeRequest,
    UserResponse,
)

router = APIRouter(prefix='/api/v1/auth', tags=['Authentication'])


def log_audit(
    db: Session,
    action: str,
    user_id: int = None,
    resource_type: str = None,
    resource_id: str = None,
    details: dict = None,
    request: Request = None
):
    """Helper to create audit log entry."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_path=str(request.url.path) if request else None,
        request_method=request.method if request else None,
    )
    db.add(audit)


# =============================================================================
# Step 1: Credentials Verification
# =============================================================================

@router.post("/login", response_model=LoginStep1Response)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Step 1: Verify credentials and send OTP.

    On success, returns a pre_auth_token (5min) and sends a 6-digit OTP
    to the user's email. The client must call /verify-otp with the OTP
    code and pre_auth_token to complete authentication.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    # Find user
    stmt = select(User).where(User.username == login_request.username.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        logger.warning("Login failed: user not found", extra={"username": login_request.username, "ip_address": ip})
        log_audit(db, "login_failed", None, "user", None,
                  {"reason": "user_not_found", "username": login_request.username}, request)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Check account lockout
    if user.is_locked():
        locked = user.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        remaining = int((locked - datetime.now(timezone.utc)).total_seconds())
        log_audit(db, "login_locked", user.id, "user", str(user.id),
                  {"reason": "account_locked", "remaining_seconds": remaining}, request)
        db.commit()
        raise HTTPException(
            status_code=423,
            detail=f"Account is temporarily locked. Try again in {max(1, remaining // 60)} minute(s)."
        )

    # Check account status
    if user.status == UserStatus.BLOCKED.value:
        log_audit(db, "login_blocked", user.id, "user", str(user.id),
                  {"reason": "account_blocked"}, request)
        db.commit()
        raise HTTPException(status_code=403, detail="Account is blocked. Contact an administrator.")

    if user.status == UserStatus.DEACTIVATED.value:
        log_audit(db, "login_failed", user.id, "user", str(user.id),
                  {"reason": "account_deactivated"}, request)
        db.commit()
        raise HTTPException(status_code=403, detail="Account has been deactivated")

    # Verify password
    if not verify_password(login_request.password, user.hashed_password):
        user.failed_login_attempts += 1

        # Check if we should lock the account
        if user.failed_login_attempts >= auth_settings.max_failed_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=auth_settings.account_lockout_minutes
            )
            log_audit(db, "account_locked", user.id, "user", str(user.id),
                      {"failed_attempts": user.failed_login_attempts}, request)
            db.commit()

            # Send account locked notification in background
            background_tasks.add_task(
                EmailService.send_account_locked_notification,
                user.email, user.full_name, auth_settings.account_lockout_minutes
            )

            raise HTTPException(
                status_code=423,
                detail=f"Account locked due to {user.failed_login_attempts} failed attempts. "
                       f"Try again in {auth_settings.account_lockout_minutes} minutes."
            )

        log_audit(db, "login_failed", user.id, "user", str(user.id),
                  {"reason": "invalid_password", "attempts": user.failed_login_attempts}, request)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Password correct — reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None

    # Determine OTP strategy
    otp_source = "email"
    otp_purpose = OTPPurpose.LOGIN.value

    # For first-time users, check if a valid welcome OTP already exists
    if user.must_change_password:
        existing_welcome = OTPService.find_valid_otp(db, user.id, OTPPurpose.WELCOME.value)
        if existing_welcome:
            # Welcome OTP still valid — tell the client to use it
            expires = existing_welcome.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            remaining_seconds = max(0, int((expires - datetime.now(timezone.utc)).total_seconds()))

            pre_auth_token = create_pre_auth_token(user.id, user.username)
            log_audit(db, "login_step1_success", user.id, "user", str(user.id),
                      {"otp_source": "welcome_email"}, request)
            db.commit()

            return LoginStep1Response(
                pre_auth_token=pre_auth_token,
                otp_sent=False,
                otp_expires_in=remaining_seconds,
                otp_source="welcome_email",
                resend_available_in=0,
                message="Enter the verification code from your welcome email."
            )

    # Generate and send a new OTP
    lifetime = OTPService.get_lifetime_seconds(otp_purpose)
    plain_otp, otp_record = OTPService.create_otp(db, user.id, otp_purpose, ip, ua)

    # Send OTP email in background
    background_tasks.add_task(
        EmailService.send_login_otp,
        user.email, plain_otp, user.full_name, lifetime
    )

    # Calculate resend availability
    _, resend_remaining = OTPService.can_resend(db, user.id, otp_purpose)

    pre_auth_token = create_pre_auth_token(user.id, user.username)

    log_audit(db, "login_step1_success", user.id, "user", str(user.id),
              {"otp_source": otp_source}, request)
    db.commit()

    return LoginStep1Response(
        pre_auth_token=pre_auth_token,
        otp_sent=True,
        otp_expires_in=lifetime,
        otp_source=otp_source,
        resend_available_in=resend_remaining,
        message="A verification code has been sent to your email."
    )


# =============================================================================
# Step 2: OTP Verification
# =============================================================================

@router.post("/verify-otp", response_model=OTPVerifyResponse)
@limiter.limit("10/minute")
async def verify_otp(
    request: Request,
    otp_request: OTPVerifyRequest,
    db: Session = Depends(get_database)
):
    """
    Step 2: Verify OTP and issue access/refresh tokens.

    Requires a valid pre_auth_token from step 1 and the 6-digit OTP code.
    On success, invalidates existing sessions (concurrent session prevention)
    and creates a new login session.
    """
    # Decode pre_auth_token
    payload = decode_token(otp_request.pre_auth_token)
    if not payload or payload.get("type") != "pre_auth":
        raise HTTPException(status_code=401, detail="Invalid or expired pre-auth token. Please login again.")

    user_id = int(payload.get("sub"))
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not user.is_active():
        raise HTTPException(status_code=401, detail="User account is not active")

    # Try verifying as login OTP first, then as welcome OTP
    success, error_msg = OTPService.verify(db, user.id, otp_request.otp_code, OTPPurpose.LOGIN.value)
    if not success:
        # Try welcome OTP for first-time users
        if user.must_change_password:
            success, error_msg = OTPService.verify(db, user.id, otp_request.otp_code, OTPPurpose.WELCOME.value)

    if not success:
        log_audit(db, "otp_verification_failed", user.id, "user", str(user.id),
                  {"error": error_msg}, request)
        db.commit()
        raise HTTPException(status_code=401, detail=error_msg)

    # --- OTP verified successfully ---

    # Invalidate existing active login sessions (concurrent session prevention)
    db.query(LoginSession).filter(
        LoginSession.user_id == user.id,
        LoginSession.is_active == True,
    ).update({
        "is_active": False,
        "logged_out_at": datetime.now(timezone.utc),
    })

    # Create new login session
    session_token = str(uuid.uuid4())
    session_expires = datetime.now(timezone.utc) + timedelta(
        hours=auth_settings.refresh_token_expire_hours
    )
    login_session = LoginSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=session_expires,
    )
    db.add(login_session)

    # Create tokens
    token_data = {"sub": str(user.id), "username": user.username, "session": session_token}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token
    refresh_expires = datetime.now(timezone.utc) + timedelta(
        hours=auth_settings.refresh_token_expire_hours
    )
    token_record = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=refresh_expires,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(token_record)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    log_audit(db, "login_success", user.id, "user", str(user.id),
              {"must_change_password": user.must_change_password}, request)
    db.commit()

    logger.info("Login successful", extra={"user_id": user.id, "username": user.username})

    return OTPVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_settings.access_token_expire_minutes * 60,
        must_change_password=user.must_change_password,
        user=UserResponse.model_validate(user),
    )


# =============================================================================
# OTP Resend
# =============================================================================

@router.post("/resend-otp", response_model=OTPResendResponse)
@limiter.limit("3/minute")
async def resend_otp(
    request: Request,
    resend_request: OTPResendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Resend OTP for login verification.

    Subject to a 2-minute cooldown between resends.
    """
    payload = decode_token(resend_request.pre_auth_token)
    if not payload or payload.get("type") != "pre_auth":
        raise HTTPException(status_code=401, detail="Invalid or expired pre-auth token. Please login again.")

    user_id = int(payload.get("sub"))
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check cooldown
    purpose = OTPPurpose.LOGIN.value
    can_resend, remaining = OTPService.can_resend(db, user.id, purpose)
    if not can_resend:
        return OTPResendResponse(
            otp_sent=False,
            otp_expires_in=0,
            resend_available_in=remaining,
            message=f"Please wait {remaining} seconds before requesting a new code."
        )

    # Generate new OTP
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    lifetime = OTPService.get_lifetime_seconds(purpose)
    plain_otp, _ = OTPService.create_otp(db, user.id, purpose, ip, ua)

    # Send email in background
    background_tasks.add_task(
        EmailService.send_login_otp,
        user.email, plain_otp, user.full_name, lifetime
    )

    _, new_remaining = OTPService.can_resend(db, user.id, purpose)

    log_audit(db, "otp_resent", user.id, "user", str(user.id), None, request)
    db.commit()

    return OTPResendResponse(
        otp_sent=True,
        otp_expires_in=lifetime,
        resend_available_in=new_remaining,
        message="A new verification code has been sent to your email."
    )


# =============================================================================
# Forgot Password Flow
# =============================================================================

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Request a password reset OTP.

    Always returns success to prevent email enumeration.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    generic_message = "If this email is registered, you will receive a verification code."

    stmt = select(User).where(User.email == forgot_request.email.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE.value:
        # Don't reveal whether the email exists
        return ForgotPasswordResponse(message=generic_message)

    # Check cooldown
    purpose = OTPPurpose.FORGOT_PASSWORD.value
    can_send, remaining = OTPService.can_resend(db, user.id, purpose)
    if not can_send:
        # Still return generic message
        return ForgotPasswordResponse(message=generic_message)

    # Generate OTP
    lifetime = OTPService.get_lifetime_seconds(purpose)
    plain_otp, _ = OTPService.create_otp(db, user.id, purpose, ip, ua)

    # Send email in background
    background_tasks.add_task(
        EmailService.send_forgot_password_otp,
        user.email, plain_otp, user.full_name, lifetime
    )

    log_audit(db, "forgot_password_requested", user.id, "user", str(user.id), None, request)
    db.commit()

    return ForgotPasswordResponse(message=generic_message)


@router.post("/verify-reset-otp", response_model=VerifyResetOTPResponse)
@limiter.limit("5/minute")
async def verify_reset_otp(
    request: Request,
    verify_request: VerifyResetOTPRequest,
    db: Session = Depends(get_database)
):
    """
    Verify the password reset OTP and issue a reset token.
    """
    stmt = select(User).where(User.email == verify_request.email.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or OTP code.")

    success, error_msg = OTPService.verify(
        db, user.id, verify_request.otp_code, OTPPurpose.FORGOT_PASSWORD.value
    )

    if not success:
        log_audit(db, "reset_otp_failed", user.id, "user", str(user.id),
                  {"error": error_msg}, request)
        db.commit()
        raise HTTPException(status_code=400, detail=error_msg)

    # Issue reset token (10min)
    reset_token = create_reset_token(user.id, user.email)

    log_audit(db, "reset_otp_verified", user.id, "user", str(user.id), None, request)
    db.commit()

    return VerifyResetOTPResponse(
        reset_token=reset_token,
        expires_in=600  # 10 minutes
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
@limiter.limit("3/minute")
async def reset_password(
    request: Request,
    reset_request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Set a new password using the reset token.

    Invalidates all sessions and refresh tokens.
    """
    # Decode reset token
    payload = decode_token(reset_request.reset_token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(status_code=401, detail="Invalid or expired reset token. Please start over.")

    user_id = int(payload.get("sub"))
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    # Validate password strength
    is_valid, strength_error = validate_password_strength(reset_request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=strength_error)

    # Check password history
    if user.password_history:
        for old_hash in user.password_history:
            if verify_otp_hash(reset_request.new_password, old_hash):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot reuse any of your last {auth_settings.password_history_count} passwords."
                )

    # Also check current password
    if verify_password(reset_request.new_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="New password must be different from your current password.")

    # Update password history
    history = list(user.password_history or [])
    history.insert(0, user.hashed_password)
    user.password_history = history[:auth_settings.password_history_count]

    # Set new password
    user.hashed_password = hash_password(reset_request.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.must_change_password = False

    # Invalidate all login sessions
    db.query(LoginSession).filter(
        LoginSession.user_id == user.id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

    # Revoke all refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True, "revoked_at": datetime.now(timezone.utc)})

    log_audit(db, "password_reset_completed", user.id, "user", str(user.id), None, request)
    db.commit()

    # Send notification email in background
    background_tasks.add_task(
        EmailService.send_password_changed_notification,
        user.email, user.full_name
    )

    return ResetPasswordResponse(message="Password reset successfully. Please login with your new password.")


# =============================================================================
# Token Refresh
# =============================================================================

@router.post("/refresh", response_model=TokenRefreshResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest,
    db: Session = Depends(get_database)
):
    """
    Refresh access token using a valid refresh token.
    """
    payload = decode_token(refresh_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Find token in database
    stmt = select(RefreshToken).where(
        RefreshToken.token == refresh_request.refresh_token,
        RefreshToken.revoked == False
    )
    token_record = db.execute(stmt).scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    # Check expiry
    expires_at = token_record.expires_at
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token has expired. Please login again.")

    # Get user
    stmt = select(User).where(User.id == token_record.user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=401, detail="User account is not active")

    # Create new access token (preserve session token from original payload)
    token_data = {"sub": str(user.id), "username": user.username}
    session_token = payload.get("session")
    if session_token:
        token_data["session"] = session_token

    access_token = create_access_token(token_data)

    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_settings.access_token_expire_minutes * 60
    )


# =============================================================================
# Logout
# =============================================================================

@router.post("/logout")
async def logout(
    request: Request,
    logout_request: LogoutRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke refresh token and invalidate login session.
    """
    # Revoke refresh token
    stmt = select(RefreshToken).where(
        RefreshToken.token == logout_request.refresh_token,
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    )
    token_record = db.execute(stmt).scalar_one_or_none()

    if token_record:
        token_record.revoked = True
        token_record.revoked_at = datetime.now(timezone.utc)

    # Invalidate login session (get session token from JWT if available)
    # Mark all active sessions for this user as logged out
    db.query(LoginSession).filter(
        LoginSession.user_id == current_user.id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

    log_audit(db, "logout", current_user.id, "user", str(current_user.id), None, request)
    db.commit()

    return {"message": "Successfully logged out"}


# =============================================================================
# Change Password
# =============================================================================

@router.post("/change-password")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Change the current user's password.

    Checks password history to prevent reuse of last N passwords.
    Invalidates all sessions and refresh tokens.
    """
    # Verify current password
    if not verify_password(password_request.current_password, current_user.hashed_password):
        log_audit(db, "password_change_failed", current_user.id, "user", str(current_user.id),
                  {"reason": "invalid_current_password"}, request)
        db.commit()
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate password strength
    is_valid, strength_error = validate_password_strength(password_request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=strength_error)

    # Check new password is different from current
    if verify_password(password_request.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Check password history
    if current_user.password_history:
        for old_hash in current_user.password_history:
            if verify_password(password_request.new_password, old_hash):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot reuse any of your last {auth_settings.password_history_count} passwords."
                )

    # Update password history
    history = list(current_user.password_history or [])
    history.insert(0, current_user.hashed_password)
    current_user.password_history = history[:auth_settings.password_history_count]

    # Update password
    current_user.hashed_password = hash_password(password_request.new_password)
    current_user.must_change_password = False
    current_user.password_changed_at = datetime.now(timezone.utc)

    # Revoke all refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True, "revoked_at": datetime.now(timezone.utc)})

    # Invalidate all login sessions
    db.query(LoginSession).filter(
        LoginSession.user_id == current_user.id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

    log_audit(db, "password_changed", current_user.id, "user", str(current_user.id), None, request)
    db.commit()

    # Send notification email in background
    background_tasks.add_task(
        EmailService.send_password_changed_notification,
        current_user.email, current_user.full_name
    )

    return {"message": "Password changed successfully. All sessions have been logged out. Please login again."}


# =============================================================================
# Current User Info
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's information."""
    return UserResponse.model_validate(current_user)
