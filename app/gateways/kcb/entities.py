from sqlalchemy import Integer, DateTime, String, Numeric, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.mysql import Base

class KcbTransaction(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    details: Mapped[String] = mapped_column(String(250), nullable=False)
    money_out: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    money_in: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    status: Mapped[String] = mapped_column(String(15), nullable=False, default="UNRECONCILED")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class WorkpayKcbTransaction(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    transaction_id: Mapped[String] = mapped_column(String(100), nullable=False)
    api_reference: Mapped[String] = mapped_column(String(100), nullable=True)
    recipient: Mapped[String] = mapped_column(String(200), nullable=True)
    amount: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    sender_fee: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    recipient_fee: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    status: Mapped[String] = mapped_column(String(15), nullable=False, default="UNRECONCILED")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class KcbDebit(KcbTransaction):
    __tablename__ = "kcb_debits"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="kcb_debits")
    __table_args__ = (UniqueConstraint('details', 'session_id', name='uq_details_session'),)


class KcbCredit(KcbTransaction):
    __tablename__ = "kcb_credits"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="kcb_credits")
    __table_args__ = (UniqueConstraint('details', 'session_id', name='uq_details_session'),)


class KcbCharge(KcbTransaction):
    __tablename__ = "kcb_charges"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="kcb_charges")
    __table_args__ = (UniqueConstraint('details', 'session_id', name='uq_details_session'),)


class WpKcbPayout(WorkpayKcbTransaction):
    __tablename__ = "wp_kcb_payouts"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="wp_kcb_payouts")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class WpKcbRefund(WorkpayKcbTransaction):
    __tablename__ = "wp_kcb_refunds"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="wp_kcb_refunds")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)
