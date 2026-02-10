"""
Authentication API Endpoints.

Provides login, token refresh, logout, forgot password, and password management.
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
    create_reset_token,
    decode_token,
)
from app.auth.config import auth_settings, validate_password_strength
from app.auth.dependencies import get_current_user
from app.sqlModels.authEntities import (
    User, RefreshToken, LoginSession, UserStatus, AuditLog,
)
from app.services.email_service import EmailService
from app.pydanticModels.authModels import (
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
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
# Login
# =============================================================================

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Verify credentials and issue access/refresh tokens.

    On success, invalidates existing sessions (concurrent session prevention)
    and creates a new login session.
    """
    ip = request.client.host if request.client else None

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

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_settings.access_token_expire_minutes * 60,
        must_change_password=user.must_change_password,
        user=UserResponse.model_validate(user),
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
    Request a password reset.

    Generates a reset token and sends it via email.
    Always returns success to prevent email enumeration.
    """
    generic_message = "If this email is registered, you will receive a password reset link."

    stmt = select(User).where(User.email == forgot_request.email.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE.value:
        # Don't reveal whether the email exists
        return ForgotPasswordResponse(message=generic_message)

    # Generate reset token (10-minute expiry)
    reset_token = create_reset_token(user.id, user.email)

    # Send email with reset token in background
    background_tasks.add_task(
        EmailService.send_forgot_password_email,
        user.email, reset_token, user.full_name
    )

    log_audit(db, "forgot_password_requested", user.id, "user", str(user.id), None, request)
    db.commit()

    return ForgotPasswordResponse(message=generic_message)


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
            if verify_password(reset_request.new_password, old_hash):
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
