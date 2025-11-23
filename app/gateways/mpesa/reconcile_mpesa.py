from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.sqlModels.mpesaEntities import *
from app.pydanticModels.mpesaModels import *
from app.gateways.mpesa.service_workpay import *
from app.gateways.mpesa.services_mpesa import  *
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
workpay_api_tid_col = wp_cols_dict.get('transaction_id')


def get_dataframes(session_id: str):
    clean_bank_data = clean_mpesa_data(session_id, FILE_CONFIGS_MPESA, MPESA_COLUMNS)
    clean_workpay_data = clean_workpay_mpesa_data(session_id, COLS_WP, FILE_CONFIGS_WORKPAY_MPESA)

    if clean_bank_data.empty or clean_workpay_data.empty:
        raise ReconciliationException("clean bank data or clean workpay data is empty")

    try:
        return {
            "mpesa_debits": get_mpesa_debits(clean_bank_data, bank_details_col, bank_debits_col, bank_reference_col),
            "mpesa_credits": get_mpesa_credits(clean_bank_data, bank_credits_col, bank_remarks_col),
            "mpesa_charges": get_mpesa_charges(clean_bank_data, bank_details_col, bank_credits_col, bank_remarks_col),
            "workpay_payouts":get_workpay_mpesa_payouts(clean_workpay_data, workpay_api_ref_col),
            "workpay_refunds": get_workpay_mpesa_refunds(clean_workpay_data, workpay_api_ref_col, workpay_remarks_col),
        }
    except Exception:
        raise

def reconcile_mpesa_payouts(session_id: str):
    try:
        dfs = get_dataframes(session_id)

        mpesa_debits = dfs.get('mpesa_debits')
        workpay_payouts = dfs.get('workpay_payouts')

        mpesa_debits[bank_reference_col] = (
            mpesa_debits[bank_reference_col].astype(str).fillna("").str.strip()
        )
        mpesa_debits[bank_details_col] = (
            mpesa_debits[bank_details_col].astype(str).fillna("").str.strip()
        )
        workpay_payouts[workpay_api_ref_col] = (
            workpay_payouts[workpay_api_ref_col].astype(str).fillna("").str.strip()
        )
        workpay_payouts[workpay_api_tid_col] = (
            workpay_payouts[workpay_api_tid_col].astype(str).fillna("").str.strip()
        )

        def is_in_bank_refs(workpay_value: str) -> bool:
            if not isinstance(workpay_value, str) or not workpay_value.strip():
                return False
            return any(workpay_value in bank_ref for bank_ref in combined_bank_refs)

        combined_bank_refs = set(mpesa_debits[bank_reference_col]) | set(mpesa_debits[bank_details_col])
        workpay_payouts[workpay_remarks_col] = np.where(
            workpay_payouts[workpay_api_ref_col].isin(combined_bank_refs)
            | workpay_payouts[workpay_api_tid_col].isin(combined_bank_refs),
            #| workpay_payouts[workpay_api_ref_col].apply(is_in_bank_refs)
            #| workpay_payouts[workpay_api_tid_col].apply(is_in_bank_refs),
            RECONCILED,
            UNRECONCILED
        )

        wp_refs = set(workpay_payouts[workpay_api_ref_col]) | set(workpay_payouts[workpay_api_tid_col])
        mpesa_debits[bank_remarks_col] = np.where(
            mpesa_debits[bank_reference_col].isin(wp_refs)
            | mpesa_debits[bank_details_col].str.contains(
                "|".join(map(re.escape, wp_refs)),
                case=False, na=False
            ),
            RECONCILED,
            UNRECONCILED
        )

        if mpesa_debits.empty or workpay_payouts.empty:
            raise ReconciliationException("Equity debits or workpay payouts is empty")

        return mpesa_debits, workpay_payouts
    except Exception:
        raise

# def reconcile_mpesa_payouts(session_id: str):
#     try:
#         dfs = get_dataframes(session_id)
#
#         mpesa_debits = dfs.get('mpesa_debits')
#         workpay_payouts = dfs.get('workpay_payouts')
#
#         # Normalize columns
#         mpesa_debits[bank_reference_col] = (
#             mpesa_debits[bank_reference_col].astype(str).fillna("").str.strip()
#         )
#         mpesa_debits[bank_details_col] = (
#             mpesa_debits[bank_details_col].astype(str).fillna("").str.strip()
#         )
#         workpay_payouts[workpay_api_ref_col] = (
#             workpay_payouts[workpay_api_ref_col].astype(str).fillna("").str.strip()
#         )
#         workpay_payouts[workpay_api_tid_col] = (
#             workpay_payouts[workpay_api_tid_col].astype(str).fillna("").str.strip()
#         )
#
#         # # Clean bank refs
#         # combined_bank_refs = set(mpesa_debits[bank_reference_col]) | set(mpesa_debits[bank_details_col])
#         # combined_bank_refs = {ref for ref in combined_bank_refs if isinstance(ref, str) and ref.strip()}
#         #
#         # # Function to check substring match
#         # def matches_bank_ref(value: str) -> bool:
#         #     if not isinstance(value, str) or not value.strip():
#         #         return False
#         #
#         #     return any(value.lower() in bank_ref.lower() for bank_ref in combined_bank_refs)
#         #
#         # # Apply logic
#         # workpay_payouts[workpay_remarks_col] = np.where(
#         #     # Exact matches
#         #     workpay_payouts[workpay_api_ref_col].isin(combined_bank_refs)
#         #     | workpay_payouts[workpay_api_tid_col].isin(combined_bank_refs)
#         #
#         #     # Substring matches (correct direction)
#         #     | workpay_payouts[workpay_api_ref_col].apply(matches_bank_ref)
#         #     | workpay_payouts[workpay_api_tid_col].apply(matches_bank_ref),
#         #
#         #     RECONCILED,
#         #     UNRECONCILED
#         # )
#
#         # Matching workpay ref (with substring matching)
#         combined_bank_refs = set(mpesa_debits[bank_reference_col]) | set(mpesa_debits[bank_details_col])
#         # Remove empty strings
#         combined_bank_refs = {ref for ref in combined_bank_refs if ref}
#
#         # Create pattern for substring matching
#         bank_refs_pattern = "|".join(map(re.escape, combined_bank_refs)) if combined_bank_refs else "^$"
#
#         workpay_payouts[workpay_remarks_col] = np.where(
#             # Exact match
#             workpay_payouts[workpay_api_ref_col].isin(combined_bank_refs)
#             | workpay_payouts[workpay_api_tid_col].isin(combined_bank_refs)
#             # Substring match - bank refs contain workpay refs
#             | workpay_payouts[workpay_api_ref_col].str.contains(
#                 bank_refs_pattern,
#                 case=False, na=False
#             )
#             | workpay_payouts[workpay_api_tid_col].str.contains(
#                 bank_refs_pattern,
#                 case=False, na=False
#             ),
#             RECONCILED,
#             UNRECONCILED
#         )
#
#         # Matching bank ref (unchanged)
#         wp_refs = set(workpay_payouts[workpay_api_ref_col]) | set(workpay_payouts[workpay_api_tid_col])
#         # Remove empty strings
#         wp_refs = {ref for ref in wp_refs if ref}
#
#         wp_refs_pattern = "|".join(map(re.escape, wp_refs)) if wp_refs else "^$"
#
#         mpesa_debits[bank_remarks_col] = np.where(
#             mpesa_debits[bank_reference_col].isin(wp_refs)
#             | mpesa_debits[bank_details_col].str.contains(
#                 wp_refs_pattern,
#                 case=False, na=False
#             ),
#             RECONCILED,
#             UNRECONCILED
#         )
#
#         if mpesa_debits.empty or workpay_payouts.empty:
#             raise ReconciliationException("Equity debits or workpay payouts is empty")
#
#         return mpesa_debits, workpay_payouts
#     except Exception:
#         raise



def save_reconciled(db:Session, session_id:str):
    try:
        mpesa_debits, workpay_payouts = reconcile_mpesa_payouts(session_id)
        dfs = get_dataframes(session_id)
        mpesa_credits = dfs.get("mpesa_credits")
        mpesa_charges =  dfs.get("mpesa_charges")
        workpay_refunds = dfs.get("workpay_refunds")

        mappings = {
            "bank_debits": [mpesa_debits, MpesaTransactionBase, MpesaDebit],
            "bank_credits": [mpesa_credits, MpesaTransactionBase, MpesaCredit],
            "bank_charges": [mpesa_charges, MpesaTransactionBase, MpesaCharge],
            "workpay_payout": [workpay_payouts, WorkpayMpesaTransactionBase, WorkpayMpesaPayout],
            "workpay_refunds": [workpay_refunds, WorkpayMpesaTransactionBase, WorkpayMpesaRefund],
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