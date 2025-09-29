from fastapi import HTTPException
import pandas as pd

from.read_data import get_workpay_equity_data, get_equity_bank_data

def equity_data_clean_up():
    df_cols = ["DATE", "NARRATIVE", "DEBIT", "CREDIT", "STATUS"]
    equity_bank = get_equity_bank_data()
    new_equity_bank = pd.DataFrame(columns= df_cols)
    try:
        #Handle date column
        if "Value Date" in equity_bank.columns:
            new_equity_bank["DATE"] = pd.to_datetime(equity_bank["Value Date"], format="%d-%m-%Y")
        else:
            new_equity_bank["DATE"] = pd.to_datetime(equity_bank["Transaction Date"], format="%d-%m-%Y")

        #Handle Debit, Credit and Balance column
        for col in ['Debit', 'Credit']:
            equity_bank[col] = equity_bank[col].astype(str).str.replace(',', '').str.split('.', expand=True)[0]
        new_equity_bank[["DEBIT", "CREDIT"]] = equity_bank[['Debit', 'Credit']].astype(
            float).fillna(0).round(0)

        #Handle narrative and status column
        new_equity_bank["NARRATIVE"] = equity_bank["Narrative"].astype(str)
        new_equity_bank["STATUS"] = "Unreconciled"
        return new_equity_bank
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"failed to clean equity bank data due to: {e}")


def workpay_equity_data_clean_up():
    df_cols = ["DATE", "REFERENCE", "METHOD", "DEBIT", "SENDER", "RECIPIENT", "STATUS"]
    workpay_equity_bank = get_workpay_equity_data()
    new_workpay_equity_bank = pd.DataFrame(columns= df_cols)
    try:
        #Handle date column
        date_placeholder = workpay_equity_bank["DATE"].str.split(" ").str[0]
        new_workpay_equity_bank["DATE"] = pd.to_datetime(date_placeholder, format="%Y-%m-%d")

        #Handle API Reference, Method, DEBIT, Sender Fee, Recipient Fee and Status columns
        new_workpay_equity_bank["REFERENCE"] = workpay_equity_bank["API Reference"].astype(str).fillna("NA").str.replace('.0', '')
        new_workpay_equity_bank["METHOD"] = workpay_equity_bank['PAYMENT METHOD'].astype(str).fillna("NA")
        new_workpay_equity_bank[["DEBIT", "SENDER", "RECIPIENT"]] = workpay_equity_bank[['AMOUNT', 'SENDER FEE','RECIPIENT FEE']].astype(
                float).fillna(0).round(0)
        new_workpay_equity_bank["STATUS"] = "Unreconciled"
        return new_workpay_equity_bank
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

