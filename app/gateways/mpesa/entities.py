from sqlalchemy import Integer, DateTime, String, Numeric, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.mysql_configs import Base

class MpesaTransaction(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    transaction_id: Mapped[String] = mapped_column(String(30), nullable=False)
    details: Mapped[String] = mapped_column(String(250), nullable=False)
    withdrawn: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    paid_in: Mapped[Numeric] = mapped_column(Numeric(12,2), nullable=True, default=0)
    status: Mapped[String] = mapped_column(String(15), nullable=False, default="UNRECONCILED")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class WorkpayMpesaTransaction(Base):
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


class MpesaWithdrawn(MpesaTransaction):
    __tablename__ = "mpesa_withdrawn"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("recon_session.id"), nullable=False, index=True)
    recon_session: Mapped["ReconciliationSession"] = relationship("ReconciliationSession", back_populates="mpesa_withdrawn")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class MpesaPaidIn(MpesaTransaction):
    __tablename__ = "mpesa_deposit"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("recon_session.id"), nullable=False, index=True)
    recon_session: Mapped["ReconciliationSession"] = relationship("ReconciliationSession", back_populates="mpesa_paid_in")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class MpesaCharge(MpesaTransaction):
    __tablename__ = "mpesa_charge"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("recon_session.id"), nullable=False, index=True)
    recon_session: Mapped["ReconciliationSession"] = relationship("ReconciliationSession", back_populates="mpesa_charges")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class WpMpesaPayout(WorkpayMpesaTransaction):
    __tablename__ = "wp_mpesa_payouts"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("recon_session.id"), nullable=False, index=True)
    recon_session: Mapped["ReconciliationSession"] = relationship("ReconciliationSession", back_populates="wp_mpesa_payouts")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


class WpMpesaRefund(WorkpayMpesaTransaction):
    __tablename__ = "wp_mpesa_refunds"

    session_id: Mapped[String] = mapped_column(String(50), ForeignKey("recon_session.id"), nullable=False, index=True)
    recon_session: Mapped["ReconciliationSession"] = relationship("ReconciliationSession", back_populates="wp_mpesa_refunds")
    __table_args__ = (UniqueConstraint('transaction_id', 'session_id', name='uq_tid_session'),)


