"""
Gateway configuration database models.

Stores gateway configurations in the database for dynamic management.
Includes approval workflow for gateway changes.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.mysql_configs import Base


class ChangeRequestStatus(str, Enum):
    """Status for gateway change requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChangeRequestType(str, Enum):
    """Type of gateway change request."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"  # Soft delete (deactivate)
    ACTIVATE = "activate"
    PERMANENT_DELETE = "permanent_delete"  # Hard delete from database


class GatewayConfig(Base):
    """
    Gateway configuration model.

    Stores gateway settings including type, display name, country, currency,
    date format, and charge keywords.
    """
    __tablename__ = "gateway_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    gateway_type = Column(String(20), nullable=False)  # 'external' or 'internal'
    display_name = Column(String(100), unique=True, nullable=False)
    country = Column(String(2), nullable=False)  # ISO 3166-1 alpha-2: KE, UG, TZ
    currency = Column(String(3), nullable=False)  # ISO 4217: KES, USD, UGX
    date_format = Column(String(20), nullable=False, default='YYYY-MM-DD')
    charge_keywords = Column(JSON, nullable=True)  # List of keywords for external gateways
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<GatewayConfig(name='{self.name}', type='{self.gateway_type}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary format matching the config structure."""
        return {
            "type": self.gateway_type,
            "display_name": self.display_name,
            "country": self.country,
            "currency": self.currency,
            "date_format": self.date_format,
            "charge_keywords": self.charge_keywords or [],
            "is_active": self.is_active,
        }


class GatewayChangeRequest(Base):
    """
    Gateway change request model.

    Tracks pending gateway changes that require admin approval.
    Users (inputters) create change requests, admins approve/reject them.
    """
    __tablename__ = "gateway_change_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Change request details
    request_type = Column(String(20), nullable=False)  # create, update, delete, activate
    status = Column(String(20), nullable=False, default=ChangeRequestStatus.PENDING.value)

    # Gateway identification (for update/delete/activate, references existing gateway)
    gateway_id = Column(Integer, ForeignKey("gateway_configs.id"), nullable=True)
    gateway_name = Column(String(50), nullable=False)  # Store name for create requests

    # Proposed changes (JSON containing the new values)
    proposed_changes = Column(JSON, nullable=False)

    # Request metadata
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Approval metadata
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    gateway = relationship("GatewayConfig", foreign_keys=[gateway_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    # Indexes
    __table_args__ = (
        Index('ix_gateway_change_status', 'status'),
        Index('ix_gateway_change_requested_by', 'requested_by_id'),
        Index('ix_gateway_change_created', 'created_at'),
    )

    def __repr__(self):
        return f"<GatewayChangeRequest(id={self.id}, type='{self.request_type}', gateway='{self.gateway_name}', status='{self.status}')>"