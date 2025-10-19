from io import BytesIO

import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz, process
from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.gateways.mpesa.entities import MpesaWithdrawn, MpesaCharge, MpesaPaidIn, WpMpesaPayout, WpMpesaRefund
from app.gateways.mpesa.models import MpesaTransactionBase, WorkpayMpesaTransactionBase
from app.gateways.mpesa.mpesa_data_process import MpesaMmf, MpesaUtility
from app.gateways.mpesa.wp_mpesa_data_process import WorkpayReconciler
from app.utils.constants import FILE_CONFIGS_MPESA, MPESA_COLUMNS, MMF_PREFIX, UTILITY_PREFIX, \
    FILE_CONFIGS_WORKPAY_MPESA, WP_COLS
from app.utils.output_writer import write_to_excel


def reconcile(mmf_df: pd.DataFrame, utility_df: pd.DataFrame, wp_mpesa_df: pd.DataFrame):
    mmf = mmf_df.copy()
    utility = utility_df.copy()
    wp_df= wp_mpesa_df.copy()
    # Helper function to reconcile matches
    def reconcile_match(wp_ref, target_df, target_col, wp_col, threshold=85):
        match = process.extractOne(wp_ref, target_df[target_col], scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            target_df.loc[target_df[target_col] == match[0], 'status'] = 'Reconciled'
            wp_df.loc[wp_df[wp_col] == wp_ref, 'status'] = 'Reconciled'

    for wp_ref in wp_df['api_reference']:
        reconcile_match(wp_ref, utility, 'details', 'api_reference')
    for wp_ref in wp_df['transaction_id']:
        reconcile_match(wp_ref, mmf, 'transaction_id', 'transaction_id')
    # Combine MMF and Utility results
    mpesa_df = pd.concat([mmf, utility], ignore_index=True)
    return mpesa_df, wp_df


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
    df_mmf = MpesaMmf(FILE_CONFIGS_MPESA, MPESA_COLUMNS, MMF_PREFIX)
    df_utility = MpesaUtility(FILE_CONFIGS_MPESA, MPESA_COLUMNS, UTILITY_PREFIX)
    df_wp_mpesa = WorkpayReconciler(FILE_CONFIGS_WORKPAY_MPESA, WP_COLS)
    mpesa_withdrawn, wp_payouts = reconcile(df_mmf.get_paid_outs(), df_utility.get_paid_outs(), df_wp_mpesa.get_payouts())

    utility_charges, utility_deposits, mmf_charges, mmf_deposits = (df_utility.get_charges(), df_utility.get_paid_ins(),
                                                                    df_mmf.get_charges(), df_mmf.get_paid_ins())
    wp_refunds = df_wp_mpesa.get_refunds()

    return mpesa_withdrawn, wp_payouts, utility_charges, mmf_charges, utility_deposits, mmf_deposits, wp_refunds


def save_reconciled(db_session, session_id):
    try:
        mpesa_withdrawn, wp_payouts, utility_charges, mmf_charges, utility_deposits, mmf_deposits, wp_refunds = generate_dataframes()
        mpesa_charges = pd.concat([mmf_charges, utility_charges], ignore_index=True)
        mpesa_deposits = pd.concat([mmf_deposits, utility_deposits], ignore_index=True)
        mappings = {'mpesa_debits': [mpesa_withdrawn, MpesaTransactionBase, MpesaWithdrawn],
                    'mpesa_deposits': [mpesa_deposits, MpesaTransactionBase, MpesaPaidIn],
                    'mpesa_charges': [mpesa_charges, MpesaTransactionBase, MpesaCharge],
                    'wp_payouts': [wp_payouts, WorkpayMpesaTransactionBase, WpMpesaPayout],
                    'wp_refunds': [wp_refunds, WorkpayMpesaTransactionBase, WpMpesaRefund]}

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
        (mpesa_debits, mpesa_credits, mpesa_charges,
         wp_payouts, wp_refunds) = load_all(db_session,MpesaWithdrawn, MpesaPaidIn, MpesaCharge,
                                                     WpMpesaPayout, WpMpesaRefund, session_id=session_id)

        mpesa_debits_schema = map_to_schema(mpesa_debits, MpesaTransactionBase)
        mpesa_credits_schema = map_to_schema(mpesa_credits, MpesaTransactionBase)
        mpesa_charges_schema = map_to_schema(mpesa_charges, MpesaTransactionBase)
        wp_payouts_schema = map_to_schema(wp_payouts, WorkpayMpesaTransactionBase)
        wp_refunds_schema = map_to_schema(wp_refunds, WorkpayMpesaTransactionBase)

        schemas = {"mpesa_debits": mpesa_debits_schema, "mpesa_credits": mpesa_credits_schema, "mpesa_charges": mpesa_charges_schema,
                   "mpesa_payouts": wp_payouts_schema, "mpesa_refunds": wp_refunds_schema}
        dataframes = {name: schema_to_dataframe(records) for name, records in schemas.items()}

        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        filename = f"Mpesa_{session_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


