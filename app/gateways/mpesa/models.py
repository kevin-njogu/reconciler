from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MpesaTransactionBase(BaseModel):
    date: datetime = Field(..., description="Transaction date")
    details: Optional[str] = Field(None, description="Transaction details")
    reference: Optional[str] = Field(None, description="Transaction reference")
    debits: Optional[float] = Field(None, description="Debit amount")
    credits: Optional[float] = Field(None, description="Credit amount")
    remarks: Optional[str] = Field(None, description="Transaction remarks or reconciliation status")
    session: str = Field(..., description="Redis session ID associated with this transaction")

    class Config:
        from_attributes = True  # Pydantic v2+ friendly


class WorkpayMpesaTransactionBase(BaseModel):
    id: Optional[int] = None
    date: datetime
    transaction_id: Optional[str] = None
    api_reference: Optional[str] = None
    recipient: Optional[str] = None
    amount: Optional[float] = None
    sender_fee: Optional[float] = None
    recipient_fee: Optional[float] = None
    processing_status: Optional[str] = None
    remarks: Optional[str] = None
    session: str

    class Config:
        from_attributes = True

