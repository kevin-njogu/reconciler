"""
Gateway configuration database models.

Stores unified gateway configurations with separate file configs for external/internal.
Includes approval workflow for gateway changes.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, UniqueConstraint, func
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


class FileConfigType(str, Enum):
    """Type of file configuration."""
    EXTERNAL = "external"
    INTERNAL = "internal"


class Gateway(Base):
    """
    Unified gateway configuration model.

    Represents a gateway like "Equity" with a single display name,
    linked to both external and internal file configurations.
    """
    __tablename__ = "gateways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String(100), unique=True, nullable=False, index=True,
                         comment="Human-readable gateway name (e.g., 'Equity Bank')")
    description = Column(Text, nullable=True, comment="Optional gateway description")

    # Location and currency (shared between external and internal)
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="SET NULL"), nullable=True,
                       comment="FK to countries table")
    currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="SET NULL"), nullable=True,
                        comment="FK to currencies table")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    country = relationship("Country", foreign_keys=[country_id])
    currency = relationship("Currency", foreign_keys=[currency_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    file_configs = relationship("GatewayFileConfig", back_populates="gateway", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Gateway(id={self.id}, display_name='{self.display_name}')>"

    def get_external_config(self):
        """Get the external file configuration."""
        for config in self.file_configs:
            if config.config_type == FileConfigType.EXTERNAL.value:
                return config
        return None

    def get_internal_config(self):
        """Get the internal file configuration."""
        for config in self.file_configs:
            if config.config_type == FileConfigType.INTERNAL.value:
                return config
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        external_config = self.get_external_config()
        internal_config = self.get_internal_config()

        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "country": {
                "id": self.country.id if self.country else None,
                "code": self.country.code if self.country else None,
                "name": self.country.name if self.country else None,
            } if self.country else None,
            "currency": {
                "id": self.currency.id if self.currency else None,
                "code": self.currency.code if self.currency else None,
                "name": self.currency.name if self.currency else None,
                "symbol": self.currency.symbol if self.currency else None,
            } if self.currency else None,
            "is_active": self.is_active,
            "external_config": external_config.to_dict() if external_config else None,
            "internal_config": internal_config.to_dict() if internal_config else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GatewayFileConfig(Base):
    """
    File configuration for a gateway (external or internal).

    Each gateway has two file configs:
    - External: For bank statements (e.g., "equity")
    - Internal: For Workpay records (e.g., "workpay_equity")
    """
    __tablename__ = "gateway_file_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gateway_id = Column(Integer, ForeignKey("gateways.id", ondelete="CASCADE"), nullable=False)

    # Configuration type
    config_type = Column(String(20), nullable=False, comment="'external' or 'internal'")

    # Unique identifier for this config (e.g., "equity" or "workpay_equity")
    name = Column(String(50), unique=True, nullable=False, index=True,
                 comment="Unique config name used in file paths")

    # File matching configuration
    filename_prefix = Column(String(100), nullable=True,
                            comment="Prefix to match uploaded files (e.g., 'Account_statement')")
    expected_filetypes = Column(JSON, nullable=True, default=lambda: ["xlsx", "xls", "csv"],
                               comment="List of expected file types")

    # Header row configuration per filetype
    header_row_config = Column(JSON, nullable=True, default=lambda: {"xlsx": 0, "xls": 0, "csv": 0},
                              comment="Rows to skip to reach headers per filetype")

    # End of data detection
    end_of_data_signal = Column(String(255), nullable=True,
                               comment="Optional text that signals end of transaction data")

    # Date format for parsing
    date_format_id = Column(Integer, ForeignKey("date_formats.id", ondelete="SET NULL"), nullable=True,
                           comment="FK to date_formats table")

    # Charge keywords (external only)
    charge_keywords = Column(JSON, nullable=True,
                            comment="Keywords to identify charges (external gateways only)")


    # Column mapping for raw file transformation
    # Maps template columns to possible source column names
    # Example: {"Date": ["Transaction Date", "Trans Date"], "Reference": ["Ref No", "TXN_ID"]}
    column_mapping = Column(JSON, nullable=True,
                           comment="Mapping from template columns to possible raw column names")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    gateway = relationship("Gateway", back_populates="file_configs")
    date_format = relationship("DateFormat", foreign_keys=[date_format_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('gateway_id', 'config_type', name='uq_gateway_config_type'),
        Index('ix_gateway_file_config_gateway', 'gateway_id'),
        Index('ix_gateway_file_config_type', 'config_type'),
    )

    def __repr__(self):
        return f"<GatewayFileConfig(id={self.id}, name='{self.name}', type='{self.config_type}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "gateway_id": self.gateway_id,
            "config_type": self.config_type,
            "name": self.name,
            "filename_prefix": self.filename_prefix,
            "expected_filetypes": self.expected_filetypes or ["xlsx", "xls", "csv"],
            "header_row_config": self.header_row_config or {"xlsx": 0, "xls": 0, "csv": 0},
            "end_of_data_signal": self.end_of_data_signal,
            "date_format": {
                "id": self.date_format.id,
                "format_string": self.date_format.format_string,
                "example": self.date_format.example,
            } if self.date_format else None,
            "charge_keywords": self.charge_keywords or [],
            "column_mapping": self.column_mapping,
            "is_active": self.is_active,
        }


# Keep old GatewayConfig for backward compatibility during migration
class GatewayConfig(Base):
    """
    Legacy gateway configuration model.

    DEPRECATED: Use Gateway and GatewayFileConfig instead.
    Kept for backward compatibility during migration.
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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

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

    # Gateway identification (legacy - points to gateway_configs)
    gateway_id = Column(Integer, ForeignKey("gateway_configs.id"), nullable=True)
    gateway_name = Column(String(50), nullable=False)

    # Unified gateway identification (new - points to gateways)
    unified_gateway_id = Column(Integer, ForeignKey("gateways.id", ondelete="SET NULL"), nullable=True)
    gateway_display_name = Column(String(100), nullable=True)  # Store display name for reference

    # Proposed changes (JSON containing the new values)
    proposed_changes = Column(JSON, nullable=False)

    # Request metadata
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Approval metadata
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    legacy_gateway = relationship("GatewayConfig", foreign_keys=[gateway_id])
    unified_gateway = relationship("Gateway", foreign_keys=[unified_gateway_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    # Indexes
    __table_args__ = (
        Index('ix_gateway_change_status', 'status'),
        Index('ix_gateway_change_requested_by', 'requested_by_id'),
        Index('ix_gateway_change_created', 'created_at'),
    )

    def __repr__(self):
        return f"<GatewayChangeRequest(id={self.id}, type='{self.request_type}', gateway='{self.gateway_display_name}', status='{self.status}')>"
