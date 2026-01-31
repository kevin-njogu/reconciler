"""
Settings Entities.

Database models for system-wide configuration settings including:
- Date formats for file parsing
- Countries and their currencies
- Reconciliation keywords (charges, reversals)
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.mysql_configs import Base


class KeywordType(str, Enum):
    """Types of reconciliation keywords."""
    CHARGE = "charge"
    REVERSAL = "reversal"


class DateFormat(Base):
    """
    Date format configuration.

    Stores available date formats for parsing uploaded files.
    Examples: YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY
    """
    __tablename__ = "date_formats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    format_string = Column(String(50), unique=True, nullable=False, comment="Python strptime format string")
    display_name = Column(String(100), nullable=False, comment="Human-readable format name")
    example = Column(String(50), nullable=False, comment="Example date in this format")
    is_default = Column(Boolean, default=False, comment="Whether this is the default format")
    is_active = Column(Boolean, default=True, comment="Whether this format is available for selection")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "format_string": self.format_string,
            "display_name": self.display_name,
            "example": self.example,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Country(Base):
    """
    Country configuration with associated currencies.

    Stores countries and their expected currencies for transaction validation.
    """
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), unique=True, nullable=False, comment="ISO 3166-1 alpha-2 or alpha-3 code")
    name = Column(String(100), nullable=False, comment="Country name")
    is_active = Column(Boolean, default=True, comment="Whether this country is available")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    currencies = relationship("Currency", back_populates="country", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_country_code", "code"),
        Index("ix_country_active", "is_active"),
    )

    def to_dict(self, include_currencies: bool = True) -> dict:
        result = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_currencies:
            result["currencies"] = [c.to_dict() for c in self.currencies]
        return result


class Currency(Base):
    """
    Currency configuration linked to a country.

    Stores currencies associated with each country.
    """
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), nullable=False, comment="ISO 4217 currency code (e.g., USD, KES)")
    name = Column(String(100), nullable=False, comment="Currency name")
    symbol = Column(String(10), nullable=True, comment="Currency symbol (e.g., $, KSh)")
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="CASCADE"), nullable=False)
    is_default = Column(Boolean, default=False, comment="Default currency for this country")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    country = relationship("Country", back_populates="currencies")

    __table_args__ = (
        Index("ix_currency_code", "code"),
        Index("ix_currency_country", "country_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "symbol": self.symbol,
            "country_id": self.country_id,
            "is_default": self.is_default,
            "is_active": self.is_active,
        }


class ReconciliationKeyword(Base):
    """
    Reconciliation keyword configuration.

    Stores keywords used to identify different transaction types:
    - Charges: Bank fees, commissions, levies
    - Reversals: Transaction reversals, refunds
    """
    __tablename__ = "reconciliation_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), nullable=False, comment="The keyword to match")
    keyword_type = Column(String(20), nullable=False, comment="Type: charge, reversal")
    description = Column(String(255), nullable=True, comment="Optional description of what this keyword matches")
    is_case_sensitive = Column(Boolean, default=False, comment="Whether matching is case-sensitive")
    is_active = Column(Boolean, default=True)
    gateway_id = Column(Integer, ForeignKey("gateway_configs.id", ondelete="SET NULL"), nullable=True,
                       comment="If set, keyword only applies to this gateway")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    gateway = relationship("GatewayConfig")

    __table_args__ = (
        Index("ix_keyword_type", "keyword_type"),
        Index("ix_keyword_active", "is_active"),
        Index("ix_keyword_gateway", "gateway_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "keyword": self.keyword,
            "keyword_type": self.keyword_type,
            "description": self.description,
            "is_case_sensitive": self.is_case_sensitive,
            "is_active": self.is_active,
            "gateway_id": self.gateway_id,
            "gateway_name": self.gateway.name if self.gateway else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemSetting(Base):
    """
    Generic system settings key-value store.

    For miscellaneous settings that don't need their own table.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="Setting key")
    value = Column(Text, nullable=True, comment="Setting value (JSON for complex values)")
    value_type = Column(String(20), default="string", comment="Type: string, number, boolean, json")
    description = Column(String(255), nullable=True, comment="Description of this setting")
    is_editable = Column(Boolean, default=True, comment="Whether users can edit this setting")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "description": self.description,
            "is_editable": self.is_editable,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
