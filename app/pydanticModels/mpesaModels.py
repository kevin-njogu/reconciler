from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class MpesaTransactionBase(BaseModel):
    receipt_no: Optional[str] = Field(
        None,
        alias="Receipt No.",
        description="Unique receipt number assigned to the transaction."
    )

    completion_time: Optional[datetime] = Field(
        None,
        alias="Completion Time",
        description="Timestamp when the transaction was completed."
    )

    details: Optional[str] = Field(
        None,
        alias="Details",
        description="Description or details of the transaction."
    )

    paid_in: Optional[float] = Field(
        None,
        alias="Paid In",
        description="Amount paid in or credited in the transaction."
    )

    withdrawn: Optional[float] = Field(
        None,
        alias="Withdrawn",
        description="Amount withdrawn or debited in the transaction."
    )

    reconciliation_status: Optional[str] = Field(
        None,
        alias="Reconciliation Status",
        description="Status indicating whether the transaction has been reconciled."
    )

    reconciliation_session: Optional[str] = Field(
        None,
        alias="Reconciliation Session",
        description="Session identifier for grouping transactions during reconciliation."
    )

    class Config:
        populate_by_name = True


class WorkpayMpesaTransactionBase(BaseModel):
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

