from fastapi import HTTPException

from .filter_data import filter_equity_bank_charges, filter_equity_bank_credits, match_transactions
from .clean_data import equity_data_clean_up, workpay_equity_data_clean_up


def reconcile():
    try:
        equity_bank_clean = equity_data_clean_up()
        equity_bank_charges = filter_equity_bank_charges(equity_bank_clean)
        equity_bank_credits = filter_equity_bank_credits(equity_bank_clean)
        equity_bank_debits, workpay_equity_data = match_transactions()

        equity_data = {"bank_charge":equity_bank_charges, "bank_credit":equity_bank_credits, "bank_debit":equity_bank_debits, "workpay_equity":workpay_equity_data}
        return equity_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to reconcile: {str(e)}")
