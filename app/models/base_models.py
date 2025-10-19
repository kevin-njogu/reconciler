# from datetime import datetime
# from typing import Optional
#
# from pydantic import BaseModel, Field
#
#
# class EquityDebitBase(BaseModel):
#     date: datetime
#     narrative: str
#     debit: float
#     status: str
#     session_id: str
#
#
# class EquityWorkpayBase(BaseModel):
#     date: datetime
#     reference: str
#     method: str
#     debit: float
#     sender: float
#     recipient: float
#     status: str
#     session_id: str
#
#
# class EquityCreditBase(BaseModel):
#     date: datetime
#     narrative: str
#     credit: float
#     status: str
#
#
# class EquityChargeBase(BaseModel):
#     date: datetime
#     narrative: str
#     debit: float
#     status: str
#
#
# class MMFDebitBase(BaseModel):
#     date: datetime
#     narrative: str
#     details: str
#     debit: float
#     status: str
#     session_id: str
#
#
# class UtilityDebitBase(BaseModel):
#     date: datetime
#     narrative: str
#     details: str
#     debit: float
#     status: str
#     session_id: str
#
#
# class MMFCreditBase(BaseModel):
#     date: datetime
#     narrative: str
#     details: str
#     credit: float
#     status: str
#
#
# class UtilityCreditBase(BaseModel):
#     date: datetime
#     narrative: str
#     details: str
#     credit: float
#     status: str
#
#
# class MpesaChargeBase(BaseModel):
#     date: datetime
#     narrative: str
#     details: str
#     debit: float
#     status: str
#
#
# class MpesaWorkpayBase(BaseModel):
#     date: datetime
#     reference: str
#     method: str
#     debit: float
#     sender: float
#     recipient: float
#     status: str
#     session_id: str
#
#
# class KcbDebitBase(BaseModel):
#     date: datetime
#     narrative: str
#     debit: float
#     reference: str
#     status: str
#     session_id: str
#
#
# class KcbWorkpayBase(BaseModel):
#     date: datetime
#     reference: str
#     method: str
#     debit: float
#     sender: float
#     recipient: float
#     status: str
#     session_id: str
#
#
# class KcbCreditBase(BaseModel):
#     date: datetime
#     narrative: str
#     credit: float
#     status: str
#
#
# class KcbChargeBase(BaseModel):
#     date: datetime
#     narrative: str
#     debit: float
#     status: str
#
#
# class WorkpayTransactionBase(BaseModel):
#     date: datetime = Field(..., description="Transaction completion date and time")
#     tid: str = Field(..., max_length=200, description="Transaction ID from M-Pesa")
#     ref: Optional[str] = Field(None, max_length=250, description="Reference number or external transaction ref")
#     method: Optional[str] = Field(None, max_length=50, description="Payment method used")
#     account: Optional[str] = Field(None, max_length=250, description="Account number or name involved")
#     curr: Optional[str] = Field("KES", max_length=10, description="Currency code (e.g. KES, USD)")
#     amount: float = Field(..., ge=0, description="Transaction amount in float")
#     sender_fee: float = Field(0.0, ge=0, description="Fee charged to sender")
#     recipient_fee: float = Field(0.0, ge=0, description="Fee charged to recipient")
#     recipient: Optional[str] = Field(None, max_length=250, description="Recipient name or identifier")
#     processing_status: Optional[str] = Field(None, max_length=50, description="Transaction processing state")
#     remark: Optional[str] = Field(None, max_length=250, description="Remarks or transaction note")
#     retries: Optional[int] = Field(0, ge=0, description="Number of processing retries")
#     country: Optional[str] = Field("Kenya", max_length=50, description="Country where transaction occurred")
#     reconciliation_status: str = Field("Unreconciled", max_length=50, description="Reconciliation state")
#     gateway: str = Field(..., max_length=50, description="Gateway name (e.g. 'mpesa')")
#     session_id: str = Field(..., description="Linked reconciliation session ID")
#
#     class Config:
#         from_attributes = True
#         str_strip_whitespace = True
#         validate_assignment = True
#
#
# class MpesaBase(BaseModel):
#     receipt_no: str = Field(..., description="Unique receipt number for the transaction")
#     completion_time: Optional[datetime] = Field(None, description="Time transaction was completed")
#     initiation_time: Optional[datetime] = Field(None, description="Time transaction was initiated")
#     details: Optional[str] = Field(None, description="Transaction details or narrative")
#     status: Optional[str] = Field(None, description="Transaction status e.g. Completed, Pending")
#     paid_in: Optional[float] = Field(0.0, description="Amount paid into the account")
#     withdrawn: Optional[float] = Field(0.0, description="Amount withdrawn from the account")
#     balance: Optional[float] = Field(0.0, description="Balance after transaction")
#     balance_confirmed: Optional[bool] = Field(False, description="Whether balance was confirmed")
#     reason_type: Optional[str] = Field(None, description="Reason type for transaction")
#     other_party: Optional[str] = Field(None, description="Other party information")
#     linked_tid: Optional[str] = Field(None, description="Linked transaction ID if any")
#     account_no: Optional[str] = Field(None, description="Account number or mobile number")
#     currency: Optional[str] = Field(None, description="Transaction currency")
#     reconciliation_status: Optional[str] = Field("Unreconciled", description="Reconciliation state")
#     gateway: Optional[str] = Field(None, description="Gateway used")
#     session_id: str = Field(..., description="Associated reconciliation session ID")
#
#     class Config:
#         from_attributes = True
#         str_strip_whitespace = True
#         validate_assignment = True
#
#
#
