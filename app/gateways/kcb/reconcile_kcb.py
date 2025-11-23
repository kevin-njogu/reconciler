from app.sqlModels.kcbEntities import *
from app.pydanticModels.kcbModels import *
from app.gateways.kcb.service_workpay import *
from app.gateways.kcb.services_kcb import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.utility_functions.constant_variables import RECONCILED, UNRECONCILED
import numpy as np
from app.utility_functions.file_configurations import *


bank_details_col = bank_cols_dict.get('details')
bank_debits_col = bank_cols_dict.get("debits")
bank_credits_col = bank_cols_dict.get("credits")
bank_reference_col = bank_cols_dict.get('reference')
bank_remarks_col = bank_cols_dict.get('remarks')
workpay_api_ref_col = wp_cols_dict.get('api_reference')
workpay_remarks_col = wp_cols_dict.get('remarks')


def get_dataframes(session_id: str):
    clean_bank_data = clean_kcb_data(session_id, FILE_CONFIGS_KCB, KCB_COLUMNS)
    clean_workpay_data = clean_workpay_kcb_data(session_id, COLS_WP, FILE_CONFIGS_WORKPAY_KCB)

    if clean_bank_data.empty or clean_workpay_data.empty:
        raise ReconciliationException("clean bank data or clean workpay data is empty")

    try:
        return {
            "kcb_debits": get_kcb_debits(clean_bank_data, bank_details_col, bank_debits_col, bank_reference_col),
            "kcb_credits": get_kcb_credits(clean_bank_data, bank_credits_col, bank_remarks_col),
            "kcb_charges": get_kcb_charges(clean_bank_data, bank_details_col, bank_credits_col, bank_remarks_col),
            "workpay_payouts":get_workpay_kcb_payouts(clean_workpay_data, workpay_api_ref_col),
            "workpay_refunds": get_workpay_kcb_refunds(clean_workpay_data, workpay_api_ref_col, workpay_remarks_col),
        }
    except Exception:
        raise


def reconcile_kcb_payouts(session_id: str):
    try:
        dfs = get_dataframes(session_id)

        kcb_debits = dfs.get('kcb_debits')
        workpay_payouts = dfs.get('workpay_payouts')

        kcb_debits[bank_reference_col] = (
            kcb_debits[bank_reference_col].astype(str).fillna("").str.strip().str.upper()
        )
        workpay_payouts[workpay_api_ref_col] = (
            workpay_payouts[workpay_api_ref_col].astype(str).fillna("").str.strip().str.upper()
        )

        reconciled_refs = set(kcb_debits[bank_reference_col])
        workpay_payouts[workpay_remarks_col] = np.where(
            workpay_payouts[workpay_api_ref_col].isin(reconciled_refs),
            RECONCILED,
            UNRECONCILED
        )

        wp_refs = set(workpay_payouts[workpay_api_ref_col])
        kcb_debits[bank_remarks_col] = np.where(
            kcb_debits[bank_reference_col].isin(wp_refs),
            RECONCILED,
            UNRECONCILED
        )

        if kcb_debits.empty or workpay_payouts.empty:
            raise ReconciliationException("Equity debits or workpay payouts is empty")

        return kcb_debits, workpay_payouts
    except Exception:
        raise


def save_reconciled(db:Session, session_id:str):
    try:
        kcb_debits, workpay_payouts = reconcile_kcb_payouts(session_id)
        dfs = get_dataframes(session_id)
        kcb_credits = dfs.get("kcb_credits")
        kcb_charges =  dfs.get("kcb_charges")
        workpay_refunds = dfs.get("workpay_refunds")

        mappings = {
            "bank_debits": [kcb_debits, KcbTransactionBase, KcbDebit],
            "bank_credits": [kcb_credits, KcbTransactionBase, KcbCredit],
            "bank_charges": [kcb_charges, KcbTransactionBase, KcbCharge],
            "workpay_payout": [workpay_payouts, WorkpayKcbTransactionBase, WorkpayKcbPayout],
            "workpay_refunds": [workpay_refunds, WorkpayKcbTransactionBase, WorkpayKcbRefund],
        }

        with db.begin():
            for key, (df, pydantic_model, entity) in mappings.items():
                if df is None or df.empty:
                    continue

                if "details" in df.columns and "session" in df.columns:
                    duplicates = df[df.duplicated(subset=["details", "session"], keep=False)]

                records = df.to_dict("records")
                validated = [pydantic_model(**rec) for rec in records]
                payload = [v.model_dump() for v in validated]

                db.bulk_insert_mappings(entity, payload)
        return "Reconciliation process completed"
    except IntegrityError as e:
        db.rollback()
        raise DbOperationException(f"Duplicate entry detected {e} ")
    except Exception:
        db.rollback()
        raise
