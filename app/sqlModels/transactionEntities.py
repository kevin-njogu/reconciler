from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.mysql_configs import Base


class Gateway(PyEnum):
    """
    Gateway/source of the transaction.

    New naming convention uses {base_gateway}_external or {base_gateway}_internal
    to clearly identify the transaction source.
    """
    # External gateways (bank statements)
    EQUITY_EXTERNAL = "equity_external"
    KCB_EXTERNAL = "kcb_external"
    MPESA_EXTERNAL = "mpesa_external"
    # Internal gateways (workpay records)
    EQUITY_INTERNAL = "equity_internal"
    KCB_INTERNAL = "kcb_internal"
    MPESA_INTERNAL = "mpesa_internal"


class TransactionType(PyEnum):
    """Type of transaction."""
    # External transaction types
    CREDIT = "credit"
    DEBIT = "debit"
    CHARGE = "charge"
    # Internal transaction types
    PAYOUT = "payout"
    REFUND = "refund"
    TOP_UP = "top_up"


class ReconciliationStatus(PyEnum):
    """Reconciliation status."""
    RECONCILED = "reconciled"
    UNRECONCILED = "unreconciled"


class AuthorizationStatus(PyEnum):
    """Authorization status for manual reconciliations."""
    PENDING = "pending"  # Awaiting admin authorization
    AUTHORIZED = "authorized"  # Approved by admin
    REJECTED = "rejected"  # Rejected by admin


class Transaction(Base):
    """
    Unified transaction table for all gateways (external and internal).

    Uses the unified template format with columns:
    - Date, Reference, Details, Debit, Credit

    The `gateway` column acts as a discriminator to identify the source:
    - External gateways: equity, kcb, mpesa (bank statements)
    - Internal gateways: workpay_equity, workpay_kcb, workpay_mpesa (internal records)

    The `transaction_type` column identifies the nature of the transaction:
    - credit, debit, charge, payout
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Discriminator column
    gateway = Column(String(50), nullable=False, index=True)

    # Transaction type
    transaction_type = Column(String(50), nullable=False, index=True)

    # Common columns (from unified template: Date, Reference, Details, Debit, Credit)
    date = Column(DateTime, nullable=True)
    transaction_id = Column(String(255), nullable=True, index=True)
    narrative = Column(String(500), nullable=True)

    # Amount columns (from unified template)
    debit = Column(Numeric(18, 2), nullable=True)
    credit = Column(Numeric(18, 2), nullable=True)

    # Reconciliation columns
    reconciliation_status = Column(String(50), nullable=True, index=True)
    batch_id = Column(String(100), ForeignKey("batches.batch_id"), nullable=False, index=True)
    reconciliation_note = Column(String(1000), nullable=True)  # "System Reconciled" or manual note
    reconciliation_key = Column(String(255), nullable=True, index=True)  # Generated match key for auditing
    source_file = Column(String(255), nullable=True)  # Source file name for tracking

    # Manual reconciliation columns
    is_manually_reconciled = Column(String(10), nullable=True, default=None)  # 'true' or None
    manual_recon_note = Column(String(1000), nullable=True)
    manual_recon_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    manual_recon_at = Column(DateTime, nullable=True)

    # Authorization columns (for manual reconciliations)
    authorization_status = Column(String(50), nullable=True, index=True)  # pending, authorized, rejected
    authorized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    authorization_note = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", backref="transactions")
    manual_reconciled_user = relationship(
        "User", foreign_keys=[manual_recon_by], backref="manual_reconciliations"
    )
    authorization_user = relationship(
        "User", foreign_keys=[authorized_by], backref="authorized_transactions"
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_gateway_batch', 'gateway', 'batch_id'),
        Index('ix_gateway_type_batch', 'gateway', 'transaction_type', 'batch_id'),
        Index('ix_recon_status_batch', 'reconciliation_status', 'batch_id'),
        Index('ix_auth_status_batch', 'authorization_status', 'batch_id'),
        Index('ix_recon_key_batch', 'reconciliation_key', 'batch_id'),
    )

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, gateway='{self.gateway}', "
            f"type='{self.transaction_type}', transaction_id='{self.transaction_id}')>"
        )

    @classmethod
    def is_external(cls, gateway: str) -> bool:
        """Check if gateway is external (bank statement)."""
        return gateway.lower().endswith("_external")

    @classmethod
    def is_internal(cls, gateway: str) -> bool:
        """Check if gateway is internal (workpay records)."""
        return gateway.lower().endswith("_internal")

    @classmethod
    def get_base_gateway(cls, gateway: str) -> str:
        """Extract base gateway name from full gateway identifier."""
        gateway_lower = gateway.lower()
        if gateway_lower.endswith("_external"):
            return gateway_lower.replace("_external", "")
        elif gateway_lower.endswith("_internal"):
            return gateway_lower.replace("_internal", "")
        return gateway_lower