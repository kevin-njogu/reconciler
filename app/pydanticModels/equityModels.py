from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class EquityTransactionBase(BaseModel):
    transaction_date: Optional[datetime] = Field(
        None, alias="Transaction Date",
        description="Date of the transaction"
    )
    narrative: Optional[str] = Field(
        None, alias="Narrative",
        description="Narration/description of the transaction"
    )
    transaction_reference: Optional[str] = Field(
        None, alias="Transaction Reference",
        description="Bank-provided transaction reference"
    )
    customer_reference: Optional[str] = Field(
        None, alias="Customer Reference",
        description="Customer-defined reference"
    )
    debit: Optional[Decimal] = Field(
        None, alias="Debit",
        description="Debit amount"
    )
    credit: Optional[Decimal] = Field(
        None, alias="Credit",
        description="Credit amount"
    )
    reconciliation_status: Optional[str] = Field(
        None, alias="Reconciliation Status",
        description="Reconciled / Unreconciled"
    )
    reconciliation_session: Optional[str] = Field(
        None, alias="Reconciliation Session",
        description="Session ID used during reconciliation"
    )

    class Config:
        populate_by_name = True
        from_attributes = True



class WorkpayEquityTransactionBase(BaseModel):
    date: Optional[datetime] = Field(
        None, alias="DATE",
        description="Date of the payout or refund"
    )
    transaction_id: Optional[str] = Field(
        None, alias="Transaction ID",
        description="Workpay transaction ID"
    )
    api_reference: Optional[str] = Field(
        None, alias="API Reference",
        description="API reference for matching with bank data"
    )
    recipient: Optional[str] = Field(
        None, alias="RECIPIENT",
        description="Recipient name or identifier"
    )
    amount: Optional[Decimal] = Field(
        None, alias="AMOUNT",
        description="Transaction amount"
    )
    status: Optional[str] = Field(
        None, alias="STATUS",
        description="Transaction status (Paid, Refunded, Failed, etc.)"
    )
    sender_fee: Optional[Decimal] = Field(
        None, alias="SENDER FEE",
        description="Fee charged to the sender"
    )
    recipient_fee: Optional[Decimal] = Field(
        None, alias="RECIPIENT FEE",
        description="Fee charged to the recipient"
    )
    reconciliation_status: Optional[str] = Field(
        None, alias="Reconciliation Status",
        description="Reconciled / Unreconciled"
    )
    reconciliation_session: Optional[str] = Field(
        None, alias="Reconciliation Session",
        description="Session ID for this reconciliation process"
    )

    class Config:
        populate_by_name = True
        from_attributes = True

