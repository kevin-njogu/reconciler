from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.gateways.equity.entities import *
from app.gateways.equity.models import *
from app.gateways.equity.service_workpay import *
from app.gateways.equity.services_equity import *
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
    clean_bank_data = clean_equity_data(session_id, FILE_CONFIGS_EQUITY, EQUITY_COLUMNS)
    clean_workpay_data = clean_workpay_equity_data(session_id, COLS_WP, FILE_CONFIGS_WORKPAY_EQUITY)

    if clean_bank_data.empty or clean_workpay_data.empty:
        raise ReconciliationException("clean bank data or clean workpay data is empty")

    try:
        return {
            "equity_debits": get_equity_debits(clean_bank_data, bank_details_col, bank_debits_col, bank_reference_col),
            "gateway_credits": get_equity_credits(clean_bank_data, bank_credits_col, bank_remarks_col),
            "gateway_charges": get_equity_charges(clean_bank_data, bank_details_col, bank_credits_col, bank_remarks_col),
            "workpay_payouts": get_workpay_equity_payouts(clean_workpay_data, workpay_api_ref_col),
            "workpay_refunds": get_workpay_equity_refunds(clean_workpay_data, workpay_api_ref_col, workpay_remarks_col),
            "workpay_topups": get_workpay_equity_top_ups(clean_workpay_data, workpay_api_ref_col, workpay_remarks_col),
        }
    except Exception:
        raise


def reconcile_equity_payouts(session_id: str):
    try:
        dfs = get_dataframes(session_id)

        equity_debits = dfs.get('equity_debits')
        workpay_payouts = dfs.get('workpay_payouts')

        equity_debits[bank_reference_col] = (
            equity_debits[bank_reference_col].astype(str).fillna("").str.strip().str.upper()
        )
        workpay_payouts[workpay_api_ref_col] = (
            workpay_payouts[workpay_api_ref_col].astype(str).fillna("").str.strip().str.upper()
        )

        reconciled_refs = set(equity_debits[bank_reference_col])
        workpay_payouts[workpay_remarks_col] = np.where(
            workpay_payouts[workpay_api_ref_col].isin(reconciled_refs),
            RECONCILED,
            UNRECONCILED
        )

        wp_refs = set(workpay_payouts[workpay_api_ref_col])
        equity_debits[bank_remarks_col] = np.where(
            equity_debits[bank_reference_col].isin(wp_refs),
            RECONCILED,
            UNRECONCILED
        )

        if equity_debits.empty or workpay_payouts.empty:
            raise ReconciliationException("Equity debits or workpay payouts is empty")

        return equity_debits, workpay_payouts
    except Exception:
        raise


def save_reconciled(db:Session, session_id:str):
    try:
        equity_debits, workpay_payouts = reconcile_equity_payouts(session_id)
        dfs = get_dataframes(session_id)
        equity_credits = dfs.get("gateway_credits")
        equity_charges =  dfs.get("gateway_charges")
        workpay_refunds = dfs.get("workpay_refunds")
        workpay_topups = dfs.get("workpay_topups")

        mappings = {
            "bank_debits": [equity_debits, EquityTransactionBase, EquityDebit],
            "bank_credits": [equity_credits, EquityTransactionBase, EquityCredit],
            "bank_charges": [equity_charges, EquityTransactionBase, EquityCharge],
            "workpay_payout": [workpay_payouts, WorkpayEquityTransactionBase, WorkpayEquityPayout],
            "workpay_refunds": [workpay_refunds, WorkpayEquityTransactionBase, WorkpayEquityRefund],
            "workpay_topups": [workpay_topups, WorkpayEquityTransactionBase, WorkpayTopUp],
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
        raise DbOperationException(f"Duplicate entry detected {e}")
    except Exception:
        db.rollback()
        raise