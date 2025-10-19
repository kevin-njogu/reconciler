from sqlalchemy import Integer, DateTime, String, Numeric, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.mysql import Base

class EquityTransaction(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    narrative: Mapped[String] = mapped_column(String(100), nullable=False)
    debit: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    credit: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    status: Mapped[String] = mapped_column(String(15), nullable=False, default="UNRECONCILED")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class WorkpayEquityTransaction(Base):
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


class EquityDebit(EquityTransaction):
    __tablename__ = "equity_debits"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="equity_debits")
    __table_args__ = (UniqueConstraint('narrative', 'session_id', name='uq_narrative_session'),)


class EquityCredit(EquityTransaction):
    __tablename__ = "equity_credits"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="equity_credits")
    __table_args__ = (UniqueConstraint('narrative', 'session_id', name='uq_narrative_session'),)


class EquityCharge(EquityTransaction):
    __tablename__ = "equity_charges"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="equity_charges")
    __table_args__ = (UniqueConstraint('narrative', 'session_id', name='uq_narrative_session'),)


class WpEquityPayout(WorkpayEquityTransaction):
    __tablename__ = "wp_equity_payouts"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="wp_equity_payouts")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class WpEquityRefund(WorkpayEquityTransaction):
    __tablename__ = "wp_equity_refunds"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="wp_equity_refunds")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class TopUp(WorkpayEquityTransaction):
    __tablename__ = "top_ups"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("session.id"), nullable=False, index=True)
    session: Mapped["Session"] = relationship("Session", back_populates="top_ups")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)