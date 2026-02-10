"""
Authentication and Authorization Database Models.

Defines User, RefreshToken, OTPToken, LoginSession, and AuditLog tables.
"""
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.mysql_configs import Base


class UserRole(PyEnum):
    """User roles for authorization."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class UserStatus(PyEnum):
    """User account status."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    DEACTIVATED = "deactivated"


class OTPPurpose(PyEnum):
    """OTP purpose types."""
    LOGIN = "login"
    WELCOME = "welcome"
    FORGOT_PASSWORD = "forgot_password"


class User(Base):
    """
    User account model.

    Stores user credentials, role, account status, and security metadata.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    mobile_number = Column(String(20), nullable=True)

    # Role and status
    role = Column(String(50), nullable=False, default=UserRole.USER.value, index=True)
    status = Column(String(50), nullable=False, default=UserStatus.ACTIVE.value, index=True)

    # Password management
    must_change_password = Column(Boolean, default=True, nullable=False)
    password_changed_at = Column(DateTime, nullable=True)
    password_history = Column(JSON, nullable=True, comment="Last N password hashes to prevent reuse")

    # Account lockout
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True, comment="Account locked until this timestamp")

    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User", remote_side=[id], backref="created_users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    otp_tokens = relationship("OTPToken", back_populates="user", cascade="all, delete-orphan")
    login_sessions = relationship("LoginSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")

    # Indexes
    __table_args__ = (
        Index('ix_user_role_status', 'role', 'status'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]

    def is_super_admin(self) -> bool:
        """Check if user is super admin."""
        return self.role == UserRole.SUPER_ADMIN.value

    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE.value

    def is_locked(self) -> bool:
        """Check if account is currently locked out."""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone
        locked = self.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return locked > datetime.now(timezone.utc)

    @property
    def full_name(self) -> str:
        """Get full name or username if names not set."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username


class RefreshToken(Base):
    """
    Refresh token storage for token management.

    Allows tracking and revocation of refresh tokens.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index('ix_refresh_token_user_revoked', 'user_id', 'revoked'),
        Index('ix_refresh_token_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"

    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        from datetime import datetime, timezone
        return not self.revoked and self.expires_at > datetime.now(timezone.utc)


class OTPToken(Base):
    """
    OTP token storage for two-factor authentication.

    Stores hashed OTP codes with purpose, expiry, and attempt tracking.
    """
    __tablename__ = "otp_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # OTP details
    otp_hash = Column(String(255), nullable=False, comment="Bcrypt hash of 6-digit OTP")
    purpose = Column(String(50), nullable=False, comment="login, welcome, or forgot_password")

    # Lifecycle
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False, comment="Wrong OTP attempts (max 3)")

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="otp_tokens")

    # Indexes
    __table_args__ = (
        Index('ix_otp_user_purpose', 'user_id', 'purpose'),
        Index('ix_otp_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<OTPToken(id={self.id}, user_id={self.user_id}, purpose='{self.purpose}')>"

    def is_expired(self) -> bool:
        """Check if OTP has expired."""
        from datetime import datetime, timezone
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < datetime.now(timezone.utc)


class LoginSession(Base):
    """
    Login session tracking.

    Records active user sessions for concurrent session management
    and audit trail.
    """
    __tablename__ = "login_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)

    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    login_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    logged_out_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="login_sessions")

    # Indexes
    __table_args__ = (
        Index('ix_session_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<LoginSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class AuditLog(Base):
    """
    Audit log for tracking user actions.

    Records all significant operations for security and compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)

    # Timestamp
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])

    # Indexes
    __table_args__ = (
        Index('ix_audit_user_action', 'user_id', 'action'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_created', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}')>"
