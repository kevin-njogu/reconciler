from fastapi import HTTPException
import pandas as pd
from app.utils.get_upload_dir import get_upload_dir


def drop_from_first_empty_row(df):
    empty_rows = df.isnull().all(axis=1)
    first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(df)
    if empty_rows.any():
        return df.loc[:first_empty_idx - 1]
    else:
        return df


def drop_last_row(df):
    df_final = df.iloc[:-1]
    return df_final


def get_equity_bank_data():
    path = get_upload_dir()
    final_equity_bank = pd.DataFrame()
    try:
        for file in path.iterdir():
            if file.name.startswith("1000"):
                if file.suffix.lower() in (".xlsx", ".xls"):
                    equity_bank = pd.read_excel(file, engine="openpyxl", skiprows=8)
                    new_equity_bank = equity_bank.iloc[:, 2:]
                    final_equity_bank = drop_from_first_empty_row(new_equity_bank)
                if file.suffix.lower() == "csv":
                    equity_bank = pd.read_csv(file, dtype=str, on_bad_lines="skip", skiprows=5)
                    final_equity_bank = drop_from_first_empty_row(equity_bank)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read equity bank data: {str(e)}")
    return final_equity_bank


def get_workpay_equity_data():
    path = get_upload_dir()
    final_workpay_equity_df = pd.DataFrame()
    try:
        for file in path.iterdir():
            if file.name.startswith("equity_payouts"):
                if file.suffix.lower() in (".xlsx", ".xls"):
                        equity_bank = pd.read_excel(file, engine="openpyxl", sheet_name="KES", na_values="nan")
                        final_workpay_equity_df = drop_last_row(equity_bank)
                if file.suffix.lower() == "csv":
                        equity_bank = pd.read_csv(file, dtype=str)
                        final_workpay_equity_df = drop_last_row(equity_bank)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read equity workpay data: {str(e)}")

    return final_workpay_equity_df