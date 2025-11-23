from io import BytesIO
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.reports.output_writer import write_to_excel
from app.sqlModels.equityEntities import *
from app.pydanticModels.equityModels import *
from app.sqlModels.kcbEntities import *
from app.pydanticModels.kcbModels import *
from app.sqlModels.mpesaEntities import *
from app.pydanticModels.mpesaModels import *


def map_to_schema(records, schema):
    return [schema.model_validate(record, from_attributes=True) for record in records]


def schema_to_dataframe(schema_records):
    return pd.DataFrame([r.model_dump() for r in schema_records])


def load_all(db_session: Session, session_id: str, *models):
    results = []
    for model in models:
        stmt = select(model).where(model.reconciliation_session == session_id)
        records = db_session.execute(stmt).scalars().all()
        results.append(records)
    return results


def map_mpesa(db_session: Session, session_id:str):
    (mpesa_debits, mpesa_credits, mpesa_charges,
     wp_payouts, wp_refunds) = load_all(db_session, session_id, MpesaDebit, MpesaCredit, MpesaCharge,
                                             WorkpayMpesaPayout, WorkpayMpesaRefund, )

    mpesa_debits_schema = map_to_schema(mpesa_debits, MpesaTransactionBase)
    mpesa_credits_schema = map_to_schema(mpesa_credits, MpesaTransactionBase)
    mpesa_charges_schema = map_to_schema(mpesa_charges, MpesaTransactionBase)
    wp_payouts_schema = map_to_schema(wp_payouts, WorkpayMpesaTransactionBase)
    wp_refunds_schema = map_to_schema(wp_refunds, WorkpayMpesaTransactionBase)
    schemas = {"mpesa_debits": mpesa_debits_schema, "mpesa_credits": mpesa_credits_schema,
               "mpesa_charges": mpesa_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema}
    return schemas


def map_equity(db_session: Session, session_id:str):
    (equity_debits, equity_credits, equity_charges,
     wp_payouts, wp_refunds, topups) = load_all(db_session, session_id, EquityDebit, EquityCredit, EquityCharge,
                                                     WorkpayEquityPayout, WorkpayEquityRefund ,WorkpayTopUp)

    equity_debits_schema = map_to_schema(equity_debits, EquityTransactionBase)
    equity_credits_schema = map_to_schema(equity_credits, EquityTransactionBase)
    equity_charges_schema = map_to_schema(equity_charges, EquityTransactionBase)
    wp_payouts_schema = map_to_schema(wp_payouts, WorkpayEquityTransactionBase)
    wp_refunds_schema = map_to_schema(wp_refunds, WorkpayEquityTransactionBase)
    topups_schema = map_to_schema(topups, WorkpayEquityTransactionBase)
    schemas = {"equity_debits": equity_debits_schema, "gateway_credits": equity_credits_schema,
               "gateway_charges": equity_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema,
               "top_ups": topups_schema}
    return schemas


def map_kcb(db_session: Session, session_id:str):
    (kcb_debits, kcb_credits, kcb_charges,
     wp_payouts, wp_refunds) = load_all(db_session, session_id, KcbDebit, KcbCredit, KcbCharge,
                                             WorkpayKcbPayout, WorkpayKcbRefund)

    kcb_debits_schema = map_to_schema(kcb_debits, KcbTransactionBase)
    kcb_credits_schema = map_to_schema(kcb_credits, KcbTransactionBase)
    kcb_charges_schema = map_to_schema(kcb_charges, KcbTransactionBase)
    wp_payouts_schema = map_to_schema(wp_payouts, WorkpayKcbTransactionBase)
    wp_refunds_schema = map_to_schema(wp_refunds, WorkpayKcbTransactionBase)
    schemas = {"kcb_debits": kcb_debits_schema, "kcb_credits": kcb_credits_schema,
               "kcb_charges": kcb_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema}
    return schemas


def download_gateway_report(db_session: Session, gateway: str, session_id: str):
    schemas = {}
    try:
        if gateway.lower() == "equity":
            schemas = map_equity(db_session, session_id)
        elif gateway.lower() == "mpesa":
            schemas = map_mpesa(db_session, session_id)
        elif gateway.lower() == "kcb":
            schemas = map_kcb(db_session, session_id)

        dataframes = {name: schema_to_dataframe(records) for name, records in schemas.items()}

        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        filename = f"{gateway.capitalize()}_{session_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers=headers)
    except Exception:
        raise