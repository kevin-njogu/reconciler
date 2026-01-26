"""
Authentication dependencies for FastAPI.

Provides dependency injection functions for authentication and authorization.
"""
from typing import Optional, List, Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database
from app.auth.security import decode_token

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_database)
):
    """
    Get the current authenticated user from the JWT token.

    Args:
        request: The incoming request.
        credentials: HTTP Bearer credentials.
        db: Database session.

    Returns:
        User object if authenticated.

    Raises:
        HTTPException 401: If not authenticated or token invalid.
    """
    # Import here to avoid circular imports
    from app.sqlModels.authEntities import User, UserStatus

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

    return user


def require_active_user(
    user = Depends(get_current_user)
):
    """
    Require an active user (not requiring password change).

    For most endpoints, we still allow users who need to change password
    to access basic functionality. This dependency enforces that they
    have changed their password.

    Args:
        user: The current authenticated user.

    Returns:
        User object if active and password changed.

    Raises:
        HTTPException 403: If user must change password.
    """
    from app.sqlModels.authEntities import UserStatus

    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=403,
            detail="Account is not active"
        )

    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required. Please change your password first.",
            headers={"X-Password-Change-Required": "true"}
        )

    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Create a dependency that requires specific roles.

    Args:
        allowed_roles: List of allowed role values.

    Returns:
        Dependency function.
    """
    def role_checker(user = Depends(require_active_user)):
        from app.sqlModels.authEntities import UserRole

        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return user

    return role_checker


def require_admin(user = Depends(require_active_user)):
    """
    Require admin or super_admin role.

    Args:
        user: The current authenticated user.

    Returns:
        User object if admin.

    Raises:
        HTTPException 403: If not admin.
    """
    from app.sqlModels.authEntities import UserRole

    if user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return user


def require_super_admin(user = Depends(require_active_user)):
    """
    Require super_admin role.

    Args:
        user: The current authenticated user.

    Returns:
        User object if super admin.

    Raises:
        HTTPException 403: If not super admin.
    """
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admin privileges required"
        )
    return user


def require_user_role(user = Depends(require_active_user)):
    """
    Require user role specifically (not admin or super_admin).

    This is for operations that should only be initiated by users (inputters),
    not by admins who should only approve.

    Args:
        user: The current authenticated user.

    Returns:
        User object if user role.

    Raises:
        HTTPException 403: If not user role.
    """
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.USER.value:
        raise HTTPException(
            status_code=403,
            detail="This operation can only be performed by users with 'user' role"
        )
    return user


def require_admin_only(user = Depends(require_active_user)):
    """
    Require admin role specifically (not super_admin).

    This is for approval operations that should only be done by admins.

    Args:
        user: The current authenticated user.

    Returns:
        User object if admin role.

    Raises:
        HTTPException 403: If not admin role.
    """
    from app.sqlModels.authEntities import UserRole

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="This operation can only be performed by users with 'admin' role"
        )
    return user
