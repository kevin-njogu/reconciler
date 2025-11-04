from sqlalchemy import Integer, DateTime, String, UniqueConstraint, Column, Float
from app.database.mysql_configs import Base


class KcbTransaction(Base):
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
        return f"<KcbTransaction(id={self.id}, reference='{self.reference}', date={self.date})>"


class WorkpayKcbTransaction(Base):
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
            f"<WorkpayKcbTransaction(id={self.id}, api_reference='{self.api_reference}', "
            f"recipient='{self.recipient}', amount={self.amount})>"
        )


class KcbDebit(KcbTransaction):
    __tablename__ = "kcb_debits"

    __table_args__ = (UniqueConstraint('reference', 'session', name='uq_reference_session'),)


class KcbCredit(KcbTransaction):
    __tablename__ = "kcb_credits"


class KcbCharge(KcbTransaction):
    __tablename__ = "kcb_charges"



class WorkpayKcbPayout(WorkpayKcbTransaction):
    __tablename__ = "workpay_kcb_payouts"


class WorkpayKcbRefund(WorkpayKcbTransaction):
    __tablename__ = "workpay_kcb_refund"