from datetime import datetime
from typing import Optional

from app.equity.model import bank_charge_model, bank_debit_model, workpay_model, bank_credit_model
from pydantic import BaseModel
from fastapi import HTTPException
from .reconcile_data import reconcile
from app.database.database_connection import get_db_session


class EquityDebitBase(BaseModel):
    date: datetime
    narrative: str
    reference: str
    debit: int
    credit: int
    status: str

class EquityWorkpayBase(BaseModel):
    date: datetime
    reference: str
    method: str
    debit: int
    sender: int
    recipient: int
    status: str

class EquityCreditBase(BaseModel):
    date: datetime
    narrative: str
    debit: int
    credit: int
    status: str

class EquityChargeBase(BaseModel):
    date: datetime
    narrative: str
    debit: int
    credit: int
    status: str


def save_to_database(records, session):
    session.add_all(records)
    session.commit()  # The context manager will handle rollback if this fails

    return {
        "message": f"Successfully inserted {len(records)} records",
        "count": len(records),
        "status": "success"
    }


def upload_service(dataframe, pydynamic_model, db_model):
    try:
        print("uploading data", dataframe.columns.tolist())
        dataframe.columns = dataframe.columns.str.lower()
        df_records = dataframe.to_dict('records')
        #convert to pydynamic models for validation
        validated_records = []
        for record in df_records:
            if isinstance(record.get('date'), str):
                record['date'] = datetime.fromisoformat(record['date'])
            validated_record = pydynamic_model(**record)
            validated_records.append(validated_record)

        # Convert to SQLAlchemy models
        db_records = []
        for record in validated_records:
            db_record = db_model(**record.dict())
            db_records.append(db_record)
        return db_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to process upload: {str(e)}")


def upload_service_impl():
    records = []
    equity_dict = reconcile()
    with get_db_session() as session:
        try:
            for name, item in equity_dict.items():
                if name == "bank_charge":
                    records = upload_service(item, EquityChargeBase, bank_charge_model.EquityCharges)
                    save_to_database(records, session)
                elif name == "bank_credit":
                    records = upload_service(item, EquityCreditBase, bank_credit_model.EquityCredit)
                    save_to_database(records, session)
                elif name == "workpay_equity":
                    records = upload_service(item, EquityWorkpayBase, workpay_model.EquityWorkpay)
                    save_to_database(records, session)
                elif name == "bank_debit":
                    records = upload_service(item, EquityDebitBase, bank_debit_model.EquityDebits)
                    save_to_database(records, session)
            return {
                    "message": f"Successfully inserted {len(records)} records",
                    "count": len(records),
                    "status": "success"
                    }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to process upload service implementation: {str(e)}")

