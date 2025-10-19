# import uuid
#
# from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, false, UniqueConstraint, Numeric, Boolean
# from app.database.database_variables import DbConfigs
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
#
# Base = DbConfigs.Base
#
# class ReconciliationSession(Base):
#     __tablename__= 'recon_session'
#
#     id = Column(String(40), primary_key=True, default=lambda: str(uuid.uuid4()))
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
#     equity_debits = relationship("EquityDebits", back_populates="session", cascade="all, delete-orphan")
#     equity_workpay = relationship("EquityWorkpay", back_populates="session", cascade="all, delete-orphan")
#     mmf_debit = relationship("MMFDebit", back_populates="session", cascade="all, delete-orphan")
#     utility_debit = relationship("UtilityDebit", back_populates="session", cascade="all, delete-orphan")
#     mpesa = relationship("MpesaTransaction", back_populates="session", cascade="all, delete-orphan")
#     mpesa_workpay = relationship("WorkpayTransaction", back_populates="session", cascade="all, delete-orphan")
#     kcb_debits = relationship("KCBDebits", back_populates="session", cascade="all, delete-orphan")
#     kcb_workpay = relationship("KCBWorkpay", back_populates="session", cascade="all, delete-orphan")
#
#
#
# class WorkpayTransaction(Base):
#     __tablename__ = 'workpay'
#
#     id = Column(Integer, primary_key=True, index=True)
#     date = Column(DateTime, index=True)
#     tid = Column(String(200), nullable=False, index=True)
#     ref = Column(String(250), nullable=True)
#     method = Column(String(50), nullable=True)
#     account = Column(String(250), nullable=True)
#     curr = Column(String(10), nullable=True)
#     amount = Column(Numeric(12, 2), nullable=False)
#     sender_fee = Column(Numeric(12, 2), nullable=False)
#     recipient_fee = Column(Numeric(12, 2), nullable=False)
#     recipient = Column(String(250), nullable=True)
#     processing_status = Column(String(50), nullable=True)
#     remark = Column(String(250), nullable=True)
#     retries = Column(Integer, nullable=True)
#     country =  Column(String(50), nullable=True)
#     reconciliation_status = Column(String(50), nullable=False, default="Unreconciled")
#     gateway = Column(String(50), nullable=False, index=True)
#     session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False, index=True)
#
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
#     session = relationship("ReconciliationSession", back_populates="mpesa_workpay")
#
#     __table_args__ = (
#         UniqueConstraint('tid', 'session_id', name='uq_tid_session'),
#                       )
#
#
#
# class MpesaTransaction(Base):
#     __tablename__ = 'mpesa'
#
#     id = Column(Integer, primary_key=True, index=True)
#     receipt_no = Column(String(100), nullable=False, index=True)
#     completion_time = Column(DateTime, nullable=True, index=True)
#     initiation_time = Column(DateTime, nullable=True)
#     details = Column(String(500), nullable=True)
#     status = Column(String(100), nullable=True)
#     paid_in = Column(Numeric(12, 2), nullable=True, default=0.0)
#     withdrawn = Column(Numeric(12, 2), nullable=True, default=0.0)
#     balance = Column(Numeric(12, 2), nullable=True, default=0.0)
#     balance_confirmed = Column(Boolean, nullable=True, default=False)
#     reason_type = Column(String(250), nullable=True)
#     other_party = Column(String(250), nullable=True)
#     linked_tid = Column(String(250), nullable=True)
#     account_no = Column(String(100), nullable=True)
#     currency = Column(String(10), nullable=True)
#     reconciliation_status = Column(String(50), nullable=False, default="Unreconciled")
#     gateway = Column(String(50), nullable=False, index=True)
#     session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False, index=True)
#
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
#     session = relationship("ReconciliationSession", back_populates="mpesa")
#
#     __table_args__ = (
#         UniqueConstraint('receipt_no', 'session_id', name='uq_receipt_no_session'),
#                       )
#
#
#
# class EquityTransaction(Base):
#     __tablename__ = 'equity'
#
#     id = Column(Integer, primary_key=True, index=True)
#     transaction_date = Column(DateTime, nullable=True, index=True)
#     value_date = Column(DateTime, nullable=True)
#     narrative = Column(String(500), nullable=True)
#     debit = Column(Numeric(12, 2), nullable=True, default=0.0)
#     credit = Column(Numeric(12, 2), nullable=True, default=0.0)
#     reconciliation_status = Column(String(50), nullable=False, default="Unreconciled")
#     session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False, index=True)
#
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
#     session = relationship("ReconciliationSession", back_populates="equity")
#
#     __table_args__ = (
#         UniqueConstraint('narrative', 'session_id', name='uq_narrative_session'),
#     )
#
#
#
# class KcbTransaction(Base):
#     __tablename__ = 'kcb'
#
#     id = Column(Integer, primary_key=True, index=True)
#     transaction_date = Column(DateTime, nullable=True, index=True)
#     value_date = Column(DateTime, nullable=True)
#     details = Column(String(500), nullable=True)
#     money_out = Column(Numeric(12, 2), nullable=True, default=0.0)
#     money_in = Column(Numeric(12, 2), nullable=True, default=0.0)
#     balance = Column(Numeric(12, 2), nullable=True, default=0.0)
#     reference = Column(String(500), nullable=True)
#     reconciliation_status = Column(String(50), nullable=False, default="Unreconciled")
#     session_id = Column(String(50), ForeignKey('recon_session.id', ondelete="CASCADE"), nullable=False, index=True)
#
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
#     session = relationship("ReconciliationSession", back_populates="kcb")
#
#     __table_args__ = (
#         UniqueConstraint('details', 'session_id', name='uq_details_session'),
#     )
#
