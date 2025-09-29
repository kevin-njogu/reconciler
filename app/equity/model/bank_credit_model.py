from sqlalchemy import Column, Integer, String, DateTime
from app.database.database_variables import Base

class EquityCredit(Base):
    __tablename__ = 'equity_credit'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    narrative = Column(String(200), unique=True)
    debit = Column(Integer)
    credit = Column(Integer)
    status = Column(String(20), index=True)