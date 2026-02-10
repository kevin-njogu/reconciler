"""
User Management API Endpoints.

Provides user CRUD operations for administrators.
Passwords are auto-generated and sent via welcome email.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.mysql_configs import get_database
from app.auth.security import hash_password, generate_secure_password
from app.auth.config import auth_settings
from app.auth.dependencies import require_admin, require_super_admin, get_current_user
from app.sqlModels.authEntities import User, RefreshToken, LoginSession, UserRole, UserStatus, AuditLog
from app.services.email_service import EmailService
from app.pydanticModels.authModels import (
    SuperAdminCreateRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserUpdateRequest,
    UserResponse,
    UserListResponse,
)

logger = logging.getLogger("app.users")

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

    This endpoint only works if no super admin exists yet.
    """
    # Check if super admin already exists
    stmt = select(User).where(User.role == UserRole.SUPER_ADMIN.value)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Super admin already exists. Contact existing super admin for access."
        )

    # Check email uniqueness
    stmt = select(User).where(
        (User.email == create_request.email) | (User.username == create_request.email)
    )
    existing_user = db.execute(stmt).scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create super admin with email as username
    user = User(
        username=create_request.email,
        email=create_request.email,
        first_name=create_request.first_name,
        last_name=create_request.last_name,
        hashed_password=hash_password(create_request.password),
        role=UserRole.SUPER_ADMIN.value,
        status=UserStatus.ACTIVE.value,
        must_change_password=False,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    log_audit(
        db, "super_admin_created", user.id, "user", str(user.id),
        {"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        request
    )
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("", response_model=UserCreateResponse, status_code=201)
async def create_user(
    request: Request,
    create_request: UserCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_super_admin)
):
    """
    Create a new user (super admin only).

    Password is auto-generated and sent via welcome email.
    The user must change their password on first login.
    """
    # Check email uniqueness
    stmt = select(User).where(
        (User.email == create_request.email) | (User.username == create_request.email)
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Auto-generate password
    initial_password = generate_secure_password()

    # Create user with email as username
    user = User(
        username=create_request.email,
        email=create_request.email,
        first_name=create_request.first_name,
        last_name=create_request.last_name,
        mobile_number=create_request.mobile_number,
        hashed_password=hash_password(initial_password),
        role=create_request.role.value,
        status=UserStatus.ACTIVE.value,
        must_change_password=True,
        created_by_id=current_user.id,
    )
    db.add(user)
    db.flush()

    # Send welcome email in background
    background_tasks.add_task(
        EmailService.send_welcome_email,
        user.email, user.email, initial_password, user.full_name
    )

    log_audit(
        db, "user_created", current_user.id, "user", str(user.id),
        {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "mobile_number": user.mobile_number,
            "created_by": current_user.username,
        },
        request
    )
    db.commit()
    db.refresh(user)

    return UserCreateResponse(
        user=UserResponse.model_validate(user),
        initial_password=initial_password,
        welcome_email_sent=True,
        message=f"User created successfully. Welcome email is being sent to {user.email}.",
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)."""
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
    """Get user details by ID (admin only)."""
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
    """Update user details (admin only)."""
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
        # Check email uniqueness
        stmt = select(User).where(
            ((User.email == update_request.email) | (User.username == update_request.email)),
            User.id != user_id
        )
        if db.execute(stmt).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        changes["email"] = {"old": user.email, "new": update_request.email}
        user.email = update_request.email
        user.username = update_request.email

    if update_request.mobile_number is not None and update_request.mobile_number != user.mobile_number:
        changes["mobile_number"] = {"old": user.mobile_number, "new": update_request.mobile_number}
        user.mobile_number = update_request.mobile_number

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
    """Block a user account (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block your own account")

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can block admin users")

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

    # Invalidate login sessions
    db.query(LoginSession).filter(
        LoginSession.user_id == user_id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

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
    """Unblock a user account (admin only)."""
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != UserStatus.BLOCKED.value:
        raise HTTPException(status_code=400, detail="User is not blocked")

    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can unblock admin users")

    user.status = UserStatus.ACTIVE.value
    # Clear any lockout as well
    user.failed_login_attempts = 0
    user.locked_until = None

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
    """Permanently deactivate a user account (super admin only)."""
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

    # Invalidate login sessions
    db.query(LoginSession).filter(
        LoginSession.user_id == user_id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin)
):
    """
    Reset a user's password (admin only).

    Auto-generates a new password and sends it via email.
    The user will be required to change their password on next login.
    """
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        if current_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can reset admin passwords")

    if user.role == UserRole.SUPER_ADMIN.value and user.id != current_user.id:
        raise HTTPException(status_code=400, detail="Cannot reset another super admin's password")

    # Auto-generate new password
    new_password = generate_secure_password()

    # Update password history
    history = list(user.password_history or [])
    history.insert(0, user.hashed_password)
    user.password_history = history[:auth_settings.password_history_count]

    user.hashed_password = hash_password(new_password)
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

    # Invalidate login sessions
    db.query(LoginSession).filter(
        LoginSession.user_id == user_id,
        LoginSession.is_active == True,
    ).update({"is_active": False, "logged_out_at": datetime.now(timezone.utc)})

    # Send email with new credentials in background
    background_tasks.add_task(
        EmailService.send_welcome_email,
        user.email, user.email, new_password, user.full_name
    )

    log_audit(
        db, "password_reset", current_user.id, "user", str(user.id),
        {"reset_by": current_user.username, "tokens_revoked": len(tokens)},
        request
    )
    db.commit()

    return {
        "message": f"Password reset for user '{user.username}'. Email is being sent.",
        "initial_password": new_password,
        "email_sent": True,
    }
