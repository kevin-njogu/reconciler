from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class KcbTransactionBase(BaseModel):
    transaction_date: datetime = Field(
        ...,
        alias="Transaction Date",
        description="The date and time when the transaction occurred."
    )
    transaction_details: Optional[str] = Field(
        None,
        alias="Transaction Details",
        description="Narrative or description of the transaction."
    )
    bank_reference_number: Optional[str] = Field(
        None,
        alias="Bank Reference Number",
        description="Unique reference number assigned by the bank."
    )
    money_out: Optional[float] = Field(
        None,
        alias="Money Out",
        description="Amount of money debited from the account."
    )
    money_in: Optional[float] = Field(
        None,
        alias="Money In",
        description="Amount of money credited to the account."
    )
    reconciliation_status: Optional[str] = Field(
        None,
        alias="Reconciliation Status",
        description="Whether the record is reconciled or unreconciled."
    )
    reconciliation_session: str = Field(
        ...,
        alias="Reconciliation Session",
        description="Unique session identifier for the reconciliation process."
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class WorkpayKcbTransactionBase(BaseModel):
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
