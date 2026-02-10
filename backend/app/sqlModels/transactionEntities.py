from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index, UniqueConstraint
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


class GatewayType(PyEnum):
    """Type of gateway - external (bank) or internal (workpay)."""
    EXTERNAL = "external"
    INTERNAL = "internal"


class TransactionType(PyEnum):
    """
    Type of transaction.

    External transaction types:
    - DEPOSIT: Credits/deposits into the account (auto-reconciled)
    - DEBIT: Withdrawals/payments from the account (reconcilable against internal payouts)
    - CHARGE: Bank fees/charges (auto-reconciled)

    Internal transaction types:
    - PAYOUT: Payments made to recipients (reconcilable against external debits)
    - REFUND: Refunds processed (non-reconcilable)
    """
    # External transaction types
    DEPOSIT = "deposit"  # Renamed from CREDIT for clarity
    DEBIT = "debit"
    CHARGE = "charge"
    # Internal transaction types
    PAYOUT = "payout"
    REFUND = "refund"


class ReconciliationStatus(PyEnum):
    """Reconciliation status."""
    RECONCILED = "reconciled"
    UNRECONCILED = "unreconciled"


class ReconciliationCategory(PyEnum):
    """
    Reconciliation category that determines how a transaction is processed.

    RECONCILABLE: Transaction participates in matching (external debits vs internal payouts)
    AUTO_RECONCILED: Transaction is automatically marked as reconciled (deposits, charges)
    NON_RECONCILABLE: Transaction is stored for record keeping but doesn't participate in matching
    """
    RECONCILABLE = "reconcilable"
    AUTO_RECONCILED = "auto_reconciled"
    NON_RECONCILABLE = "non_reconcilable"


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
    - External gateways: equity_external, kcb_external, mpesa_external (bank statements)
    - Internal gateways: equity_internal, kcb_internal, mpesa_internal (internal records)

    Enhanced discriminators:
    - `gateway_type`: 'external' or 'internal' - identifies source type
    - `transaction_type`: nature of transaction (deposit, debit, charge, payout, etc.)
    - `reconciliation_category`: determines reconciliation behavior
        - 'reconcilable': participates in matching (external debits, internal payouts)
        - 'auto_reconciled': automatically reconciled (deposits, charges)
        - 'non_reconcilable': stored for record keeping (refunds)
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Discriminator columns
    gateway = Column(String(50), nullable=False, index=True)
    gateway_type = Column(String(20), nullable=True, index=True)  # external, internal

    # Transaction type and reconciliation category
    transaction_type = Column(String(50), nullable=False, index=True)
    reconciliation_category = Column(String(30), nullable=True, index=True)  # reconcilable, auto_reconciled, non_reconcilable

    # Common columns (from unified template: Date, Reference, Details, Debit, Credit)
    date = Column(DateTime, nullable=True)
    transaction_id = Column(String(255), nullable=True, index=True)
    narrative = Column(String(500), nullable=True)

    # Amount columns (from unified template)
    debit = Column(Numeric(18, 2), nullable=True)
    credit = Column(Numeric(18, 2), nullable=True)

    # Reconciliation columns
    reconciliation_status = Column(String(50), nullable=True, index=True)
    run_id = Column(String(100), ForeignKey("reconciliation_runs.run_id"), nullable=True, index=True)
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
    run = relationship("ReconciliationRun", backref="transactions")
    manual_reconciled_user = relationship(
        "User", foreign_keys=[manual_recon_by], backref="manual_reconciliations"
    )
    authorization_user = relationship(
        "User", foreign_keys=[authorized_by], backref="authorized_transactions"
    )

    # Composite indexes and constraints
    __table_args__ = (
        UniqueConstraint('reconciliation_key', 'gateway', name='uq_recon_key_gateway'),
        Index('ix_gateway_run', 'gateway', 'run_id'),
        Index('ix_gateway_type_run', 'gateway', 'transaction_type', 'run_id'),
        Index('ix_recon_status_run', 'reconciliation_status', 'run_id'),
        Index('ix_auth_status_run', 'authorization_status', 'run_id'),
        Index('ix_recon_key_run', 'reconciliation_key', 'run_id'),
        Index('ix_recon_category_run', 'reconciliation_category', 'run_id'),
        Index('ix_gateway_type_category', 'gateway_type', 'reconciliation_category', 'run_id'),
        Index('ix_txn_gateway_recon_status', 'gateway', 'reconciliation_status'),
        Index('ix_txn_date', 'date'),
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

    @classmethod
    def get_gateway_type(cls, gateway: str) -> str:
        """
        Get gateway type from gateway identifier.

        Args:
            gateway: Full gateway identifier (e.g., "equity_external")

        Returns:
            'external' or 'internal'
        """
        if cls.is_external(gateway):
            return GatewayType.EXTERNAL.value
        return GatewayType.INTERNAL.value

    @classmethod
    def get_reconciliation_category(cls, transaction_type: str) -> str:
        """
        Determine reconciliation category based on transaction type.

        Categories:
        - RECONCILABLE: DEBIT (external), PAYOUT (internal)
        - AUTO_RECONCILED: DEPOSIT (external), CHARGE (external)
        - NON_RECONCILABLE: REFUND (internal)

        Args:
            transaction_type: Transaction type value

        Returns:
            Reconciliation category value
        """
        type_lower = transaction_type.lower()

        # Reconcilable transactions participate in matching
        if type_lower in [TransactionType.DEBIT.value, TransactionType.PAYOUT.value]:
            return ReconciliationCategory.RECONCILABLE.value

        # Auto-reconciled transactions are automatically marked as reconciled
        if type_lower in [TransactionType.DEPOSIT.value, TransactionType.CHARGE.value]:
            return ReconciliationCategory.AUTO_RECONCILED.value

        # Non-reconcilable transactions are stored for record keeping
        if type_lower == TransactionType.REFUND.value:
            return ReconciliationCategory.NON_RECONCILABLE.value

        # Default to reconcilable for unknown types
        return ReconciliationCategory.RECONCILABLE.value
