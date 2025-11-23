from sqlalchemy import Integer, DateTime, String, UniqueConstraint, Column, Float, Numeric
from app.database.mysql_configs import Base


class KcbTransaction(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)

    transaction_date = Column(DateTime, nullable=False)
    transaction_details = Column(String(255), nullable=True)
    bank_reference_number = Column(String(100), index=True, nullable=True)

    money_out = Column(Float, nullable=True)
    money_in = Column(Float, nullable=True)

    reconciliation_status = Column(String(50), nullable=True)
    reconciliation_session = Column(String(100), index=True, nullable=False)

    def __repr__(self):
        return (
            f"<GatewayTransactionBase(id={self.id}, "
            f"bank_reference_number='{self.bank_reference_number}', "
            f"transaction_date={self.transaction_date})>"
        )


class WorkpayKcbTransaction(Base):
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


class KcbDebit(KcbTransaction):
    __tablename__ = "kcb_debits"

    __table_args__ = (UniqueConstraint('transaction_details', 'reconciliation_session', name='uq_details_session'),)


class KcbCredit(KcbTransaction):
    __tablename__ = "kcb_credits"


class KcbCharge(KcbTransaction):
    __tablename__ = "kcb_charges"



class WorkpayKcbPayout(WorkpayKcbTransaction):
    __tablename__ = "workpay_kcb_payouts"


class WorkpayKcbRefund(WorkpayKcbTransaction):
    __tablename__ = "workpay_kcb_refund"