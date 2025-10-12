import uuid

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from app.database.database_variables import DbConfigs
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = DbConfigs.Base

class ReconciliationSession(Base):
    __tablename__= 'recon_session'

    id = Column(String(40), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    equity_debits = relationship("EquityDebits", back_populates="session", cascade="all, delete-orphan")
    equity_workpay = relationship("EquityWorkpay", back_populates="session", cascade="all, delete-orphan")
    mmf_debit = relationship("MMFDebit", back_populates="session", cascade="all, delete-orphan")
    utility_debit = relationship("UtilityDebit", back_populates="session", cascade="all, delete-orphan")
    mpesa_workpay = relationship("WorkpayMpesaTransaction", back_populates="session", cascade="all, delete-orphan")
    kcb_debits = relationship("KCBDebits", back_populates="session", cascade="all, delete-orphan")
    kcb_workpay = relationship("KCBWorkpay", back_populates="session", cascade="all, delete-orphan")


class EquityDebits(Base):
    __tablename__ = 'equity_debits'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200))
    debit = Column(Float)
    reference = Column(String(20), unique=True)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="equity_debits")


class EquityCredit(Base):
    __tablename__ = 'equity_credit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    credit = Column(Float)
    status = Column(String(20), index=True)


class EquityCharges(Base):
    __tablename__ = 'equity_charges'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    debit = Column(Float)
    status = Column(String(20), index=True)


class EquityWorkpay(Base):
    __tablename__ = 'equity_workpay'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    reference = Column(String(20), unique=True)
    method = Column(String(200))
    debit = Column(Float)
    sender = Column(Float)
    recipient = Column(Float)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="equity_workpay")


class MMFDebit(Base):
    __tablename__ = 'mmf_debit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    details = Column(String(400))
    debit = Column(Float)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="mmf_debit")


class UtilityDebit(Base):
    __tablename__ = 'utility_debit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    details = Column(String(400))
    debit = Column(Float)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="utility_debit")


class MMFCredit(Base):
    __tablename__ = 'mmf_credit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    details = Column(String(400))
    credit = Column(Float)
    status = Column(String(20), index=True)


class UtilityCredit(Base):
    __tablename__ = 'utility_credit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    details = Column(String(400))
    credit = Column(Float)
    status = Column(String(20), index=True)


class MpesaCharges(Base):
    __tablename__ = 'mpesa_charges'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    details = Column(String(400))
    debit = Column(Float)
    status = Column(String(20), index=True)


class WorkpayMpesaTransaction(Base):
    __tablename__ = 'mpesa_workpay'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    reference = Column(String(200), unique=True)
    method = Column(String(100), index=True)
    debit = Column(Float)
    sender = Column(Float)
    recipient = Column(Float)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="mpesa_workpay")


class KCBDebits(Base):
    __tablename__ = 'kcb_debits'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200))
    debit = Column(Float)
    reference = Column(String(20), unique=True)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="kcb_debits")


class KCBCredit(Base):
    __tablename__ = 'kcb_credit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    credit = Column(Float)
    status = Column(String(20), index=True)


class KCBCharges(Base):
    __tablename__ = 'kcb_charges'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    debit = Column(Float)
    status = Column(String(20), index=True)


class KCBWorkpay(Base):
    __tablename__ = 'kcb_workpay'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    reference = Column(String(20), unique=True)
    method = Column(String(200))
    debit = Column(Float)
    sender = Column(Float)
    recipient = Column(Float)
    status = Column(String(20), index=True)
    session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False)
    session = relationship("ReconciliationSession", back_populates="kcb_workpay")



