from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from app.database.mysql_configs import Base

class EquityTransaction(Base):
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
        return f"<EquityTransaction(id={self.id}, reference='{self.reference}', date={self.date})>"


class WorkpayEquityTransaction(Base):
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
            f"<WorkpayEquityTransaction(id={self.id}, api_reference='{self.api_reference}', "
            f"recipient='{self.recipient}', amount={self.amount})>"
        )


class EquityDebit(EquityTransaction):
    __tablename__ = "equity_debits"

    __table_args__ = (UniqueConstraint('details', 'session',  name='uq_details_session'),)


class EquityCredit(EquityTransaction):
    __tablename__ = "equity_credits"


class EquityCharge(EquityTransaction):
    __tablename__ = "equity_charges"


class WorkpayEquityPayout(WorkpayEquityTransaction):
    __tablename__ = "workpay_equity_payouts"


class WorkpayEquityRefund(WorkpayEquityTransaction):
    __tablename__ = "workpay_equity_refunds"


class WorkpayTopUp(WorkpayEquityTransaction):
    __tablename__ = "workpay_top_ups"
