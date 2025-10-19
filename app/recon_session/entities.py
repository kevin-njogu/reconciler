import uuid
from typing import List
from app.gateways.equity.entities import *
from app.gateways.kcb.entities import KcbCharge
from app.gateways.kcb.entities import KcbCredit
from app.gateways.kcb.entities import KcbDebit


class ReconciliationSession(Base):
    __tablename__ = "recon_session"

    id = mapped_column(String(40), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[DateTime] =  mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), server_onupdate=func.now())

    equity_debits: Mapped[List["EquityDebit"]] = relationship("EquityDebit", back_populates="recon_session", cascade="all, delete-orphan")
    equity_credits: Mapped[List["EquityCredit"]] = relationship("EquityCredit", back_populates="recon_session", cascade="all, delete-orphan")
    equity_charges: Mapped[List["EquityCharge"]] = relationship("EquityCharge", back_populates="recon_session", cascade="all, delete-orphan")

    wp_equity_payouts: Mapped[List["WpEquityPayout"]] = relationship("WpEquityPayout", back_populates="recon_session", cascade="all, delete-orphan")
    wp_equity_refunds: Mapped[List["WpEquityRefund"]] = relationship("WpEquityRefund", back_populates="recon_session", cascade="all, delete-orphan")
    top_ups: Mapped[List["TopUp"]] = relationship("TopUp", back_populates="recon_session", cascade="all, delete-orphan")

    mpesa_withdrawn: Mapped[List["MpesaWithdrawn"]] = relationship("MpesaWithdrawn", back_populates="recon_session", cascade="all, delete-orphan")
    mpesa_paid_in: Mapped[List["MpesaPaidIn"]] = relationship("MpesaPaidIn", back_populates="recon_session", cascade="all, delete-orphan")
    mpesa_charges: Mapped[List["MpesaCharge"]] = relationship("MpesaCharge", back_populates="recon_session", cascade="all, delete-orphan")

    wp_mpesa_payouts: Mapped[List["WpMpesaPayout"]] = relationship("WpMpesaPayout", back_populates="recon_session", cascade="all, delete-orphan")
    wp_mpesa_refunds: Mapped[List["WpMpesaRefund"]] = relationship("WpMpesaRefund", back_populates="recon_session", cascade="all, delete-orphan")

    kcb_debits: Mapped[List["KcbDebit"]] = relationship("KcbDebit", back_populates="recon_session", cascade="all, delete-orphan")
    kcb_credits: Mapped[List["KcbCredit"]] = relationship("KcbCredit", back_populates="recon_session", cascade="all, delete-orphan")
    kcb_charges: Mapped[List["KcbCharge"]] = relationship("KcbCharge", back_populates="recon_session", cascade="all, delete-orphan")

    wp_kcb_payouts: Mapped[List["WpKcbPayout"]] = relationship("WpKcbPayout", back_populates="recon_session", cascade="all, delete-orphan")
    wp_kcb_refunds: Mapped[List["WpKcbRefund"]] = relationship("WpKcbRefund", back_populates="recon_session", cascade="all, delete-orphan")


    # def __repr__(self) -> str:
    #     return f"ReconciliationSession(session_id={self.id!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})"

