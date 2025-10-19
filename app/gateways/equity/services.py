from io import BytesIO

import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz, process
from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.gateways.equity.entities import *
from app.gateways.equity.equity_bank_data_process import EquityReconciler
from app.gateways.equity.models import EquityTransactionBase, WorkpayEquityTransactionBase
from app.gateways.equity.wp_equity_data_process import WorkpayReconciler
from app.utils.constants import FILE_CONFIGS_WORKPAY_EQUITY, FILE_CONFIGS_EQUITY, WP_COLS
from app.utils.output_writer import write_to_excel


def reconcile(equity_df: pd.DataFrame, wp_equity_df: pd.DataFrame):
    eq_df = equity_df.copy()
    wp_df = wp_equity_df.copy()
    # Loop through workpay_df rows
    for i, ref in enumerate(wp_df['api_reference']):
        # Find best fuzzy match in equity_df['narrative']
        match = process.extractOne(ref, eq_df['narrative'], scorer=fuzz.partial_ratio)
        if match and match[1] >= 85:
            eq_mask = eq_df['narrative'] == match[0]
            wp_mask = wp_df['api_reference'] == ref
            eq_df.loc[eq_mask, 'status'] = 'Reconciled'
            wp_df.loc[wp_mask, 'status'] = 'Reconciled'
    return eq_df, wp_df


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
    wp_equity = WorkpayReconciler(FILE_CONFIGS_WORKPAY_EQUITY, WP_COLS)
    equity = EquityReconciler(FILE_CONFIGS_EQUITY)
    equity_dr, wp_dr = equity.get_debits(), wp_equity.get_payouts()
    eq_debits, wp_payouts = reconcile(equity_dr, wp_dr)
    eq_charges, eq_credits = equity.get_charges(), equity.get_credits()
    wp_refunds, top_ups = wp_equity.get_refunds(), wp_equity.get_top_ups()
    return eq_debits, wp_payouts, eq_charges, eq_credits, wp_refunds, top_ups


def save_reconciled(db_session, session_id):
    try:
        eq_debits, wp_payouts, eq_charges, eq_credits, wp_refunds, top_ups = generate_dataframes()
        mappings = {'eq_debits': [eq_debits, EquityTransactionBase, EquityDebit],
                    'eq_credits': [eq_credits, EquityTransactionBase, EquityCredit],
                    'eq_charges': [eq_charges, EquityTransactionBase, EquityCharge],
                    'wp_payouts': [wp_payouts, WorkpayEquityTransactionBase, WpEquityPayout],
                    'wp_refunds': [wp_refunds, WorkpayEquityTransactionBase, WpEquityRefund],
                    'top_ups': [top_ups, WorkpayEquityTransactionBase, TopUp]}

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
        (equity_debits, equity_credits, equity_charges,
         wp_payouts, wp_refunds, top_ups) = load_all(db_session,EquityDebit, EquityCredit, EquityCharge,
                                                     WpEquityPayout, WpEquityRefund, TopUp, session_id=session_id)

        eq_debits_schema = map_to_schema(equity_debits, EquityTransactionBase)
        eq_credits_schema = map_to_schema(equity_credits, EquityTransactionBase)
        eq_charges_schema = map_to_schema(equity_charges, EquityTransactionBase)
        wp_payouts_schema = map_to_schema(wp_payouts, WorkpayEquityTransactionBase)
        wp_refunds_schema = map_to_schema(wp_refunds, WorkpayEquityTransactionBase)
        top_ups = map_to_schema(top_ups, WorkpayEquityTransactionBase)

        schemas = {"eq_debits": eq_debits_schema, "eq_credits": eq_credits_schema, "eq_charges": eq_charges_schema,
                   "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema, "top_ups": top_ups,}
        dataframes = {name: schema_to_dataframe(records) for name, records in schemas.items()}

        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        filename = f"Equity_{session_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
