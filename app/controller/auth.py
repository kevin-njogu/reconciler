"""
Authentication API Endpoints.

Provides login, logout, token refresh, and password management.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database

logger = logging.getLogger("app.auth")
from app.auth.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.config import auth_settings
from app.auth.dependencies import get_current_user
from app.sqlModels.authEntities import User, RefreshToken, UserStatus, AuditLog
from app.pydanticModels.authModels import (
    LoginRequest,
    LoginResponse,
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


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_request: LoginRequest,
    db: Session = Depends(get_database)
):
    """
    Authenticate user and return access/refresh tokens.

    Args:
        request: The HTTP request.
        login_request: Username and password.
        db: Database session.

    Returns:
        LoginResponse with tokens and user info.

    Raises:
        HTTPException 401: If credentials invalid.
        HTTPException 403: If account blocked/deactivated.
    """
    # Find user by username
    stmt = select(User).where(User.username == login_request.username.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        logger.warning(
            f"Login failed: user not found",
            extra={
                "username": login_request.username,
                "ip_address": request.client.host if request.client else None,
            }
        )
        log_audit(
            db, "login_failed", None, "user", None,
            {"reason": "user_not_found", "username": login_request.username},
            request
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Verify password
    if not verify_password(login_request.password, user.hashed_password):
        logger.warning(
            f"Login failed: invalid password",
            extra={
                "user_id": user.id,
                "username": user.username,
                "ip_address": request.client.host if request.client else None,
            }
        )
        log_audit(
            db, "login_failed", user.id, "user", str(user.id),
            {"reason": "invalid_password"},
            request
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Check account status
    if user.status == UserStatus.BLOCKED.value:
        log_audit(
            db, "login_blocked", user.id, "user", str(user.id),
            {"reason": "account_blocked"},
            request
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Account is blocked. Contact an administrator.")

    if user.status == UserStatus.DEACTIVATED.value:
        log_audit(
            db, "login_failed", user.id, "user", str(user.id),
            {"reason": "account_deactivated"},
            request
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Account has been deactivated")

    # Create tokens
    access_token = create_access_token({"sub": str(user.id), "username": user.username})
    refresh_token = create_refresh_token({"sub": str(user.id), "username": user.username})

    # Store refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=auth_settings.refresh_token_expire_days)
    token_record = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=expires_at,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(token_record)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Audit log
    log_audit(
        db, "login_success", user.id, "user", str(user.id),
        {"must_change_password": user.must_change_password},
        request
    )
    db.commit()

    logger.info(
        f"Login successful",
        extra={
            "user_id": user.id,
            "username": user.username,
            "ip_address": request.client.host if request.client else None,
        }
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_settings.access_token_expire_minutes * 60,
        must_change_password=user.must_change_password,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest,
    db: Session = Depends(get_database)
):
    """
    Refresh access token using a valid refresh token.

    Args:
        request: The HTTP request.
        refresh_request: The refresh token.
        db: Database session.

    Returns:
        TokenRefreshResponse with new access token.

    Raises:
        HTTPException 401: If refresh token invalid or expired.
    """
    # Decode refresh token
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

    # Compare datetimes - handle both naive and aware datetimes from DB
    expires_at = token_record.expires_at
    now = datetime.now(timezone.utc)
    # If expires_at is naive, assume it's UTC and make it aware
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    # Get user
    stmt = select(User).where(User.id == token_record.user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=401, detail="User account is not active")

    # Create new access token
    access_token = create_access_token({"sub": str(user.id), "username": user.username})

    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: LogoutRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a refresh token (logout).

    Args:
        request: The HTTP request.
        logout_request: The refresh token to revoke.
        db: Database session.
        current_user: The authenticated user.

    Returns:
        Success message.
    """
    # Find and revoke the token
    stmt = select(RefreshToken).where(
        RefreshToken.token == logout_request.refresh_token,
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    )
    token_record = db.execute(stmt).scalar_one_or_none()

    if token_record:
        token_record.revoked = True
        token_record.revoked_at = datetime.now(timezone.utc)

    log_audit(
        db, "logout", current_user.id, "user", str(current_user.id),
        None, request
    )
    db.commit()

    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Change the current user's password.

    Args:
        request: The HTTP request.
        password_request: Current and new password.
        db: Database session.
        current_user: The authenticated user.

    Returns:
        Success message.

    Raises:
        HTTPException 400: If current password incorrect or new password same as old.
    """
    # Verify current password
    if not verify_password(password_request.current_password, current_user.hashed_password):
        log_audit(
            db, "password_change_failed", current_user.id, "user", str(current_user.id),
            {"reason": "invalid_current_password"},
            request
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Check new password is different
    if verify_password(password_request.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Update password
    current_user.hashed_password = hash_password(password_request.new_password)
    current_user.must_change_password = False

    # Revoke all refresh tokens
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    )
    tokens = db.execute(stmt).scalars().all()
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

    log_audit(
        db, "password_changed", current_user.id, "user", str(current_user.id),
        {"tokens_revoked": len(tokens)},
        request
    )
    db.commit()

    return {"message": "Password changed successfully. All sessions have been logged out."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's information.

    Args:
        current_user: The authenticated user.

    Returns:
        UserResponse with user details.
    """
    return UserResponse.model_validate(current_user)
