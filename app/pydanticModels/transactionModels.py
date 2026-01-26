from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class GatewayEnum(str, Enum):
    """
    Gateway/source of the transaction.

    Uses {base_gateway}_external or {base_gateway}_internal format
    to clearly identify transaction source.
    """
    # External gateways (bank statements)
    EQUITY_EXTERNAL = "equity_external"
    KCB_EXTERNAL = "kcb_external"
    MPESA_EXTERNAL = "mpesa_external"
    # Internal gateways (workpay records)
    EQUITY_INTERNAL = "equity_internal"
    KCB_INTERNAL = "kcb_internal"
    MPESA_INTERNAL = "mpesa_internal"


class TransactionTypeEnum(str, Enum):
    """Type of transaction."""
    # External transaction types
    CREDIT = "credit"
    DEBIT = "debit"
    CHARGE = "charge"
    # Internal transaction types
    PAYOUT = "payout"
    REFUND = "refund"
    TOP_UP = "top_up"


class ReconciliationStatusEnum(str, Enum):
    """Reconciliation status."""
    RECONCILED = "reconciled"
    UNRECONCILED = "unreconciled"


class TransactionBase(BaseModel):
    """
    Unified transaction model for all gateways.

    Uses the unified template format with columns:
    - Date, Reference, Details, Debit, Credit

    transaction_type distinguishes: credit, debit, charge, payout
    """
    # Discriminator
    gateway: str = Field(..., description="Gateway source (equity, kcb, mpesa, workpay_equity, etc.)")

    # Transaction type
    transaction_type: str = Field(..., description="Type of transaction")

    # Common columns (from unified template)
    date: Optional[datetime] = Field(None, alias="Date", description="Transaction date")
    transaction_id: Optional[str] = Field(None, alias="Reference", description="Unique transaction identifier")
    narrative: Optional[str] = Field(None, alias="Details", description="Transaction narration/description")

    # Amount columns (from unified template)
    debit: Optional[Decimal] = Field(None, alias="Debit", description="Debit amount")
    credit: Optional[Decimal] = Field(None, alias="Credit", description="Credit amount")

    # Reconciliation
    reconciliation_status: Optional[str] = Field(
        None, alias="Reconciliation Status", description="Reconciled/Unreconciled"
    )
    batch_id: str = Field(..., alias="Batch Id", description="Batch ID for this reconciliation")

    class Config:
        populate_by_name = True
        from_attributes = True


class TransactionCreate(BaseModel):
    """
    Unified model for creating transactions from the reconciliation engine.

    Uses the unified template format with columns:
    - Date, Reference, Details, Debit, Credit
    """
    gateway: str = Field(..., description="Gateway source (e.g., equity_external, equity_internal)")
    transaction_type: str = Field(..., description="Type: credit, debit, charge, payout")
    date: Optional[datetime] = Field(None, alias="Date")
    transaction_id: Optional[str] = Field(None, alias="Reference")
    narrative: Optional[str] = Field(None, alias="Details")
    debit: Optional[Decimal] = Field(None, alias="Debit")
    credit: Optional[Decimal] = Field(None, alias="Credit")
    reconciliation_status: Optional[str] = Field(None, alias="Reconciliation Status")
    batch_id: str = Field(..., alias="Batch Id")
    reconciliation_note: Optional[str] = Field(None, alias="Reconciliation Note")
    reconciliation_key: Optional[str] = Field(None, alias="Reconciliation Key", description="Generated match key")
    source_file: Optional[str] = Field(None, alias="Source File", description="Source filename")
    is_manually_reconciled: Optional[str] = Field(None, alias="is_manually_reconciled", description="Manual reconciliation flag")

    class Config:
        populate_by_name = True
        from_attributes = True


class TransactionResponse(BaseModel):
    """Response model for transactions."""
    id: int
    gateway: str
    transaction_type: str
    date: Optional[datetime] = None
    transaction_id: Optional[str] = None
    narrative: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    reconciliation_status: Optional[str] = None
    reconciliation_note: Optional[str] = None
    reconciliation_key: Optional[str] = None
    source_file: Optional[str] = None
    batch_id: str

    # Manual reconciliation fields
    is_manually_reconciled: Optional[str] = None
    manual_recon_note: Optional[str] = None
    manual_recon_by: Optional[int] = None
    manual_recon_at: Optional[datetime] = None

    # Authorization fields (for manual reconciliations)
    authorization_status: Optional[str] = None
    authorized_by: Optional[int] = None
    authorized_at: Optional[datetime] = None
    authorization_note: Optional[str] = None

    # Timestamps
    created_at: datetime

    class Config:
        from_attributes = True


class ReconciliationSummary(BaseModel):
    """Summary of reconciliation results (legacy format for backwards compatibility)."""
    batch_id: str
    external_gateway: str
    internal_gateway: str
    total_external_debits: int
    total_internal_records: int
    matched: int
    unmatched_external: int
    unmatched_internal: int
    total_credits: int
    total_charges: int


class ReconciliationResult(BaseModel):
    """New reconciliation result format."""
    message: str
    batch_id: str
    gateway: str
    summary: dict
    saved: dict