from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KcbTransactionBase(BaseModel):
    date: Optional[datetime]
    details: str = Field(max_length=250)
    money_out: float = Field(default=0)
    money_in: float = Field(default=0)
    status: str = Field(default="UNRECONCILED", max_length=15)


class WorkpayKcbTransactionBase(BaseModel):
    date: Optional[datetime]
    transaction_id:str = Field(max_length=100)
    api_reference: Optional[str] = Field(max_length=100)
    recipient: Optional[str] = Field(max_length=100)
    amount: float = Field(default=0)
    sender_fee: float = Field(default=0)
    recipient_fee: float = Field(default=0)
    status: str = Field(default="UNRECONCILED", max_length=15)
