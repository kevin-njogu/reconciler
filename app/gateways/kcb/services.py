from io import BytesIO

import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz, process
from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.gateways.kcb.entities import KcbDebit, KcbCredit, KcbCharge, WpKcbPayout, WpKcbRefund
from app.gateways.kcb.kcb_bank_data_process import KcbReconciler
from app.gateways.kcb.models import KcbTransactionBase, WorkpayKcbTransactionBase
from app.gateways.kcb.wp_kcb_data_process import WorkpayReconciler
from app.utils.constants import FILE_CONFIGS_WORKPAY_KCB, WP_COLS, FILE_CONFIGS_KCB, KCB_COLUMNS
from app.utils.output_writer import write_to_excel


def reconcile(gateway_df: pd.DataFrame, workpay_df: pd.DataFrame):
    gateway = gateway_df.copy()
    workpay = workpay_df.copy()
    # Loop through workpay_df rows
    for i, ref in enumerate(workpay['api_reference']):
        # Find best fuzzy match in equity_df['narrative']
        match = process.extractOne(ref, gateway['details'], scorer=fuzz.partial_ratio)
        if match and match[1] >= 85:
            gateway_mask = gateway['details'] == match[0]
            workpay_mask = workpay['api_reference'] == ref
            gateway.loc[gateway_mask, 'status'] = 'Reconciled'
            workpay.loc[workpay_mask, 'status'] = 'Reconciled'
    return gateway, workpay


def create_db_records(df: pd.DataFrame, pydantic_model, db_model, session_id:str):
    try:
        records = df.to_dict('records')
        validated_records = [pydantic_model(**record) for record in records]
        db_records = [db_model(**record.model_dump(), session_id=session_id) for record in validated_records]
        print(db_records)
        return db_records
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def generate_dataframes():
    workpay = WorkpayReconciler(FILE_CONFIGS_WORKPAY_KCB, WP_COLS)
    gateway = KcbReconciler(FILE_CONFIGS_KCB, KCB_COLUMNS)
    gateway_debits, workpay_payouts = reconcile(gateway.get_debits(), workpay.get_payouts())
    gateway_charges, gateway_credits = gateway.get_charges(), gateway.get_credits()
    workpay_refunds = workpay.get_refunds()
    return gateway_debits, workpay_payouts, gateway_charges, gateway_credits, workpay_refunds


def save_reconciled(db_session, session_id):
    try:
        gateway_name = "kcb"
        gateway_debits, workpay_payouts, gateway_charges, gateway_credits, workpay_refunds = generate_dataframes()
        mappings = {f'{gateway_name}_debits': [gateway_debits, KcbTransactionBase, KcbDebit],
                    f'{gateway_name}_credits': [gateway_credits, KcbTransactionBase, KcbCredit],
                    f'{gateway_name}_charges': [gateway_charges, KcbTransactionBase, KcbCharge],
                    f'{gateway_name}wp_payouts': [workpay_payouts, WorkpayKcbTransactionBase, WpKcbPayout],
                    f'{gateway_name}wp_refunds': [workpay_refunds, WorkpayKcbTransactionBase, WpKcbRefund]}

        for k, (df, schema, model) in mappings.items():
            db_record = create_db_records(df, schema, model, session_id)
            db_session.add_all(db_record)
            db_session.commit()

        return "Reconciliation process completed"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def map_to_schema(records, schema):
    return [schema.model_validate(record, from_attributes=True) for record in records]


def schema_to_dataframe(schema_records):
    return pd.DataFrame([r.model_dump() for r in schema_records])


def load_all(db, *models, session_id: str):
    results = []
    for model in models:
        stmt = select(model).where(model.session_id == session_id)
        records = db.execute(stmt).scalars().all()
        results.append(records)
    return results


def download_report(db_session, session_id):
    try:
        (gateway_debits, gateway_credits, gateway_charges,
         workpay_payouts, workpay_refunds) = load_all(db_session,KcbDebit, KcbCredit, KcbCharge,
                                                     WpKcbPayout, WpKcbRefund, session_id=session_id)

        gateway_debits_schema = map_to_schema(gateway_debits, KcbTransactionBase)
        gateway_credits_schema = map_to_schema(gateway_credits, KcbTransactionBase)
        gateway_charges_schema = map_to_schema(gateway_charges, KcbTransactionBase)
        workpay_payouts_schema = map_to_schema(workpay_payouts, WorkpayKcbTransactionBase)
        workpay_refunds_schema = map_to_schema(workpay_refunds, WorkpayKcbTransactionBase)

        schemas = {"kcb_debits": gateway_debits_schema, "kcb_credits": gateway_credits_schema, "kcb_charges": gateway_charges_schema,
                   "workpay_payouts": workpay_payouts_schema, "workpay_refunds": workpay_refunds_schema}
        dataframes = {name: schema_to_dataframe(records) for name, records in schemas.items()}

        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        filename = f"KCB_{session_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
