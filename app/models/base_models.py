from datetime import datetime
from pydantic import BaseModel


class EquityDebitBase(BaseModel):
    date: datetime
    narrative: str
    debit: float
    reference: str
    status: str
    session_id: str


class EquityWorkpayBase(BaseModel):
    date: datetime
    reference: str
    method: str
    debit: float
    sender: float
    recipient: float
    status: str
    session_id: str


class EquityCreditBase(BaseModel):
    date: datetime
    narrative: str
    credit: float
    status: str


class EquityChargeBase(BaseModel):
    date: datetime
    narrative: str
    debit: float
    status: str


class MMFDebitBase(BaseModel):
    date: datetime
    narrative: str
    details: str
    debit: float
    status: str
    session_id: str


class UtilityDebitBase(BaseModel):
    date: datetime
    narrative: str
    details: str
    debit: float
    status: str
    session_id: str


class MMFCreditBase(BaseModel):
    date: datetime
    narrative: str
    details: str
    credit: float
    status: str


class UtilityCreditBase(BaseModel):
    date: datetime
    narrative: str
    details: str
    credit: float
    status: str


class MpesaChargeBase(BaseModel):
    date: datetime
    narrative: str
    details: str
    debit: float
    status: str


class MpesaWorkpayBase(BaseModel):
    date: datetime
    reference: str
    method: str
    debit: float
    sender: float
    recipient: float
    status: str
    session_id: str


class KcbDebitBase(BaseModel):
    date: datetime
    narrative: str
    debit: float
    reference: str
    status: str
    session_id: str


class KcbWorkpayBase(BaseModel):
    date: datetime
    reference: str
    method: str
    debit: float
    sender: float
    recipient: float
    status: str
    session_id: str


class KcbCreditBase(BaseModel):
    date: datetime
    narrative: str
    credit: float
    status: str


class KcbChargeBase(BaseModel):
    date: datetime
    narrative: str
    debit: float
    status: str









