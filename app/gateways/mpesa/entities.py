from sqlalchemy import Integer, DateTime, String, UniqueConstraint, Column, Float
from app.database.mysql_configs import Base

class MpesaTransaction(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    details = Column(String(255), nullable=True)
    reference = Column(String(100), index=True, nullable=True)
    debits = Column(Float, nullable=True)
    credits = Column(Float, nullable=True)
    remarks = Column(String(100), nullable=True)
    session = Column(String(100), index=True, nullable=False)

    def __repr__(self):
        return f"<MpesaTransaction(id={self.id}, reference='{self.reference}', date={self.date})>"


class WorkpayMpesaTransaction(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    transaction_id = Column(String(100), index=True, nullable=True)
    api_reference = Column(String(100), index=True, nullable=True)
    recipient = Column(String(255), nullable=True)
    amount = Column(Float, nullable=True)
    sender_fee = Column(Float, nullable=True)
    recipient_fee = Column(Float, nullable=True)
    processing_status = Column(String(50), nullable=True)
    remarks = Column(String(255), nullable=True)
    session = Column(String(100), index=True, nullable=False)

    def __repr__(self):
        return (
            f"<WorkpayMpesaTransaction(id={self.id}, api_reference='{self.api_reference}', "
            f"recipient='{self.recipient}', amount={self.amount})>"
        )


class MpesaDebit(MpesaTransaction):
    __tablename__ = "mpesa_debits"

    __table_args__ = (UniqueConstraint('reference', name='uq_reference'),)


class MpesaCredit(MpesaTransaction):
    __tablename__ = "mpesa_credits"


class MpesaCharge(MpesaTransaction):
    __tablename__ = "mpesa_charges"


class WorkpayMpesaPayout(WorkpayMpesaTransaction):
    __tablename__ = "workpay_mpesa_payouts"


class WorkpayMpesaRefund(WorkpayMpesaTransaction):
    __tablename__ = "workpay_mpesa_refund"

