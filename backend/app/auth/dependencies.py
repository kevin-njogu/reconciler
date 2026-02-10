"""
Authentication dependencies for FastAPI.

Provides dependency injection functions for authentication and authorization.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database
from app.auth.security import decode_token
from app.auth.config import auth_settings

logger = logging.getLogger("app.auth.dependencies")

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_database)
):
    """
    Get the current authenticated user from the JWT token.

    Also validates the login session is still active (concurrent session prevention).

    Raises:
        HTTPException 401: If not authenticated or token invalid.
    """
    from app.sqlModels.authEntities import User, UserStatus, LoginSession

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == int(user_id))
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is blocked or deactivated
    if user.status == UserStatus.BLOCKED.value:
        raise HTTPException(
            status_code=403,
            detail="Account is blocked. Contact an administrator."
        )

    if user.status == UserStatus.DEACTIVATED.value:
        raise HTTPException(
            status_code=403,
            detail="Account has been deactivated"
        )

    # Validate login session is still active (concurrent session prevention)
    session_token = payload.get("session")
    if session_token:
        stmt = select(LoginSession).where(
            LoginSession.session_token == session_token,
            LoginSession.user_id == user.id,
            LoginSession.is_active == True,
        )
        session = db.execute(stmt).scalar_one_or_none()
        if not session:
            logger.warning(
                "Session invalidated for user %s (session: %s)",
                user.id, session_token[:8] + "..."
            )
            raise HTTPException(
                status_code=401,
                detail="Session has been invalidated. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


def require_active_user(
    user = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Require an active user who has changed their password.

    Also checks for 90-day password expiry and auto-sets must_change_password.

    Raises:
        HTTPException 403: If user must change password or account inactive.
    """
    from app.sqlModels.authEntities import UserStatus

    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=403,
            detail="Account is not active"
        )

    # Check 90-day password expiry
    if auth_settings.password_expiry_days > 0 and not user.must_change_password:
        if user.password_changed_at:
            changed = user.password_changed_at
            if changed.tzinfo is None:
                changed = changed.replace(tzinfo=timezone.utc)
            expiry_date = changed + timedelta(days=auth_settings.password_expiry_days)
            if datetime.now(timezone.utc) > expiry_date:
                user.must_change_password = True
                db.commit()

    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required. Please change your password first.",
            headers={"X-Password-Change-Required": "true"}
        )

    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """Create a dependency that requires specific roles."""
    def role_checker(user = Depends(require_active_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return user

    return role_checker


def require_admin(user = Depends(require_active_user)):
    """Require admin or super_admin role."""
    from app.sqlModels.authEntities import UserRole

    if user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return user


def require_super_admin(user = Depends(require_active_user)):
    """Require super_admin role."""
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admin privileges required"
        )
    return user


def require_user_role(user = Depends(require_active_user)):
    """Require user role specifically (not admin or super_admin)."""
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.USER.value:
        raise HTTPException(
            status_code=403,
            detail="This operation can only be performed by users with 'user' role"
        )
    return user


def require_admin_only(user = Depends(require_active_user)):
    """Require admin role specifically (not super_admin)."""
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="This operation can only be performed by users with 'admin' role"
        )
    return user
