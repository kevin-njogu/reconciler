from sqlalchemy import Integer, DateTime, String, UniqueConstraint, Column, Float, Numeric
from app.database.mysql_configs import Base

class MpesaTransaction(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    receipt_no = Column(String(100), index=True, nullable=False)
    completion_time = Column(DateTime, nullable=False)
    details = Column(String(255), nullable=True)
    paid_in = Column(Float, nullable=True)
    withdrawn = Column(Float, nullable=True)
    reconciliation_status = Column(String(50), nullable=True)
    reconciliation_session = Column(String(100), index=True, nullable=False)

    def __repr__(self):
        return (
            f"<MpesaTransaction(id={self.id}, receipt_no='{self.receipt_no}', "
            f"completion_time={self.completion_time})>"
        )


class WorkpayMpesaTransaction(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=True)
    transaction_id = Column(String(150), index=True, nullable=True)
    api_reference = Column(String(150), index=True, nullable=True)
    recipient = Column(String(255), nullable=True)
    amount = Column(Numeric(18, 2), nullable=True)
    status = Column(String(50), nullable=True)
    sender_fee = Column(Numeric(18, 2), nullable=True)
    recipient_fee = Column(Numeric(18, 2), nullable=True)
    reconciliation_status = Column(String(50), nullable=True)
    reconciliation_session = Column(String(100), index=True, nullable=False)

    def __repr__(self):
        return (
            f"<WorkpayEquityTransaction(id={self.id}, api_reference='{self.api_reference}', "
            f"amount={self.amount}, status='{self.status}')>"
        )


class MpesaDebit(MpesaTransaction):
    __tablename__ = "mpesa_debits"

    __table_args__ = (UniqueConstraint('receipt_no', 'reconciliation_session',  name='uq_reference_session'),)


class MpesaCredit(MpesaTransaction):
    __tablename__ = "mpesa_credits"


class MpesaCharge(MpesaTransaction):
    __tablename__ = "mpesa_charges"


class WorkpayMpesaPayout(WorkpayMpesaTransaction):
    __tablename__ = "workpay_mpesa_payouts"


class WorkpayMpesaRefund(WorkpayMpesaTransaction):
    __tablename__ = "workpay_mpesa_refund"

