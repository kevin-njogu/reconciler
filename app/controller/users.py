"""
User Management API Endpoints.

Provides user CRUD operations for administrators.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database
from app.auth.security import hash_password
from app.auth.config import auth_settings
from app.auth.dependencies import require_admin, require_super_admin, get_current_user
from app.sqlModels.authEntities import User, RefreshToken, UserRole, UserStatus, AuditLog
from app.pydanticModels.authModels import (
    SuperAdminCreateRequest,
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserListResponse,
    PasswordResetRequest,
)

router = APIRouter(prefix='/api/v1/users', tags=['User Management'])


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


@router.post("/create-super-admin", response_model=UserResponse, status_code=201)
async def create_super_admin(
    request: Request,
    create_request: SuperAdminCreateRequest,
    db: Session = Depends(get_database)
):
    """
    Create the first super admin user.

    This endpoint only works if:
    1. No super admin exists in the system
    2. The correct secret key is provided

    Args:
        request: The HTTP request.
        create_request: Super admin creation details with secret key.
        db: Database session.

    Returns:
        Created super admin user.

    Raises:
        HTTPException 400: If super admin exists or secret invalid.
    """
    # Verify secret key
    if create_request.secret_key != auth_settings.super_admin_secret:
        log_audit(
            db, "super_admin_creation_failed", None, "user", None,
            {"reason": "invalid_secret"},
            request
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid secret key")

    # Check if super admin already exists
    stmt = select(User).where(User.role == UserRole.SUPER_ADMIN.value)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Super admin already exists. Contact existing super admin for access."
        )

    # Check email uniqueness (also check username since username = email)
    stmt = select(User).where(
        (User.email == create_request.email) | (User.username == create_request.email)
    )
    existing_user = db.execute(stmt).scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create super admin with email as username
    user = User(
        username=create_request.email,  # Use email as username
        email=create_request.email,
        first_name=create_request.first_name,
        last_name=create_request.last_name,
        hashed_password=hash_password(create_request.password),
        role=UserRole.SUPER_ADMIN.value,
        status=UserStatus.ACTIVE.value,
        must_change_password=False,  # Super admin doesn't need to change password
    )
    db.add(user)
    db.flush()  # Get the ID

    log_audit(
        db, "super_admin_created", user.id, "user", str(user.id),
        {"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        request
    )
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: Request,
    create_request: UserCreateRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_super_admin)
):
    """
    Create a new user (super admin only).

    The username is automatically set to the user's email address.

    Args:
        request: The HTTP request.
        create_request: User creation details (first_name, last_name, email, password, role).
        db: Database session.
        current_user: The authenticated super admin user.

    Returns:
        Created user.

    Raises:
        HTTPException 400: If email already exists.
    """
    # Check email uniqueness (also checks username since username = email)
    stmt = select(User).where(
        (User.email == create_request.email) | (User.username == create_request.email)
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user with email as username
    user = User(
        username=create_request.email,  # Use email as username
        email=create_request.email,
        first_name=create_request.first_name,
        last_name=create_request.last_name,
        hashed_password=hash_password(create_request.password),
        role=create_request.role.value,
        status=UserStatus.ACTIVE.value,
        must_change_password=True,  # New users must change password
        created_by_id=current_user.id,
    )
    db.add(user)
    db.flush()

    log_audit(
        db, "user_created", current_user.id, "user", str(user.id),
        {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "created_by": current_user.username
        },
        request
    )
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    List all users (admin only).

    Args:
        role: Optional filter by role.
        status: Optional filter by status.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        List of users.
    """
    conditions = []

    if role:
        if role.lower() not in [r.value for r in UserRole]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
            )
        conditions.append(User.role == role.lower())

    if status:
        if status.lower() not in [s.value for s in UserStatus]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in UserStatus]}"
            )
        conditions.append(User.status == status.lower())

    stmt = select(User)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(User.created_at.desc())

    users = db.execute(stmt).scalars().all()

    return UserListResponse(
        count=len(users),
        users=[UserResponse.model_validate(u) for u in users]
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Get user details by ID (admin only).

    Args:
        user_id: User ID to retrieve.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        User details.

    Raises:
        HTTPException 404: If user not found.
    """
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    update_request: UserUpdateRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Update user details (admin only).

    Args:
        user_id: User ID to update.
        request: The HTTP request.
        update_request: Fields to update.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        Updated user.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 403: If insufficient permissions.
    """
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only super admin can modify other admins or super admins
    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can modify admin users")

    # Only super admin can assign admin/super_admin roles
    if update_request.role and update_request.role.value in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can assign admin roles")

    # Track changes
    changes = {}

    if update_request.email is not None and update_request.email != user.email:
        # Check email uniqueness (also check username since username = email)
        stmt = select(User).where(
            ((User.email == update_request.email) | (User.username == update_request.email)),
            User.id != user_id
        )
        if db.execute(stmt).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        changes["email"] = {"old": user.email, "new": update_request.email}
        user.email = update_request.email
        user.username = update_request.email  # Keep username in sync with email

    if update_request.role is not None and update_request.role.value != user.role:
        changes["role"] = {"old": user.role, "new": update_request.role.value}
        user.role = update_request.role.value

    if changes:
        log_audit(
            db, "user_updated", current_user.id, "user", str(user.id),
            {"changes": changes, "updated_by": current_user.username},
            request
        )
        db.commit()
        db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/{user_id}/block")
async def block_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Block a user account (admin only).

    Args:
        user_id: User ID to block.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        Success message.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 400: If trying to block self or super admin.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block your own account")

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only super admin can block other admins
    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can block admin users")

    # Cannot block super admin
    if user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=400, detail="Cannot block a super admin")

    user.status = UserStatus.BLOCKED.value

    # Revoke all refresh tokens
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    )
    tokens = db.execute(stmt).scalars().all()
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

    log_audit(
        db, "user_blocked", current_user.id, "user", str(user.id),
        {"blocked_by": current_user.username, "tokens_revoked": len(tokens)},
        request
    )
    db.commit()

    return {"message": f"User '{user.username}' has been blocked"}


@router.post("/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Unblock a user account (admin only).

    Args:
        user_id: User ID to unblock.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        Success message.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 400: If user not blocked.
    """
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != UserStatus.BLOCKED.value:
        raise HTTPException(status_code=400, detail="User is not blocked")

    # Only super admin can unblock admin users
    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can unblock admin users")

    user.status = UserStatus.ACTIVE.value

    log_audit(
        db, "user_unblocked", current_user.id, "user", str(user.id),
        {"unblocked_by": current_user.username},
        request
    )
    db.commit()

    return {"message": f"User '{user.username}' has been unblocked"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_super_admin)
):
    """
    Permanently deactivate a user account (super admin only).

    Args:
        user_id: User ID to deactivate.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated super admin user.

    Returns:
        Success message.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 400: If trying to deactivate self or another super admin.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=400, detail="Cannot deactivate a super admin")

    user.status = UserStatus.DEACTIVATED.value

    # Revoke all refresh tokens
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    )
    tokens = db.execute(stmt).scalars().all()
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

    log_audit(
        db, "user_deactivated", current_user.id, "user", str(user.id),
        {"deactivated_by": current_user.username},
        request
    )
    db.commit()

    return {"message": f"User '{user.username}' has been permanently deactivated"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Reset a user's password (admin only).

    The user will be required to change their password on next login.

    Args:
        user_id: User ID whose password to reset.
        request: The HTTP request.
        reset_request: New password.
        db: Database session.
        current_user: The authenticated admin user.

    Returns:
        Success message.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 403: If insufficient permissions.
    """
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only super admin can reset admin passwords
    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can reset admin passwords")

    # Cannot reset super admin password
    if user.role == UserRole.SUPER_ADMIN.value and user.id != current_user.id:
        raise HTTPException(status_code=400, detail="Cannot reset another super admin's password")

    user.hashed_password = hash_password(reset_request.new_password)
    user.must_change_password = True

    # Revoke all refresh tokens
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    )
    tokens = db.execute(stmt).scalars().all()
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

    log_audit(
        db, "password_reset", current_user.id, "user", str(user.id),
        {"reset_by": current_user.username, "tokens_revoked": len(tokens)},
        request
    )
    db.commit()

    return {"message": f"Password reset for user '{user.username}'. User must change password on next login."}
