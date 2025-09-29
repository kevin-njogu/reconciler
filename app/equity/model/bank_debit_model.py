from sqlalchemy import Column, Integer, String, DateTime
from app.database.database_variables import Base

class EquityDebits(Base):
    __tablename__ = 'equity_debits'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200))
    reference = Column(String(20), unique=True)
    debit = Column(Integer)
    credit = Column(Integer)
    status = Column(String(20), index=True)
