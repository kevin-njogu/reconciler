from sqlalchemy import Column, Integer, String, DateTime
from app.database.database_variables import Base


class EquityWorkpay(Base):
    __tablename__ = 'equity_workpay'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    reference = Column(String(20))
    method = Column(String(200), index=True)
    debit = Column(Integer)
    sender = Column(Integer)
    recipient = Column(Integer)
    status = Column(String(20), index=True)