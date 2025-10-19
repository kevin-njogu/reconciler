from datetime import datetime
from typing import List

import pandas as pd
from fastapi import HTTPException

from app.utils.constants import FILE_CONFIGS_KCB, KCB_COLUMNS, UNRECONCILED, RECONCILED
from app.utils.read_recon_files import read_file


STATUS_COL = 'status'

class KcbReconciler:

    def __init__(self, configs, columns):
        self.configs = configs
        self.df = None
        self.columns = columns


    def handle_date(self, df: pd.DataFrame, trn_date: str, value_date: str, new_date: str):
        df[new_date] = datetime.today()
        if trn_date not in df.columns:
            df[new_date] = df[value_date]
        else:
            df[new_date] = df[trn_date]
        df[new_date] = (df[new_date].astype(str).str.strip().apply(pd.to_datetime, errors='coerce', format="%d.%m.%Y"))
        return df


    def read_file(self) -> pd.DataFrame:
        try:
            file_prefix = self.configs.get("kcb_prefix_excel")
            sheet_name = self.configs.get("sheet_name")
            skip_excel = self.configs.get("excel_rows")
            skip_csv = self.configs.get("csv_rows")
            self.df = read_file(filename_prefix=file_prefix, sheet_name=sheet_name, excel_skip_rows=skip_excel, csv_skip_rows=skip_csv)
            return self.df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    # noinspection PyUnresolvedReferences
    def clean_data(self) -> pd.DataFrame:
        try:
            columns = self.columns
            trn_date = self.columns.get("transaction_date")
            value_date = self.columns.get("value_date")
            new_date = "Date"
            old_df_cols = [columns.get(k) for k in ["details", "money_out", "money_in"]]
            old_df_cols.insert(0, "Date")
            new_df_cols = ["date", "details", "money_out", "money_in"]

            if self.df is None:
                self.read_file()
            raw_df = self.df
            dropped_first_row_df = raw_df.iloc[1:].copy()
            #Handle date columns
            dropped_first_row_df = self.handle_date(dropped_first_row_df, trn_date, value_date, new_date)
            #Handle other str cols
            str_cols = [columns.get("details"), columns.get("reference")]
            dropped_first_row_df.loc[:, str_cols] = dropped_first_row_df[str_cols].astype('string').fillna("NA").apply(lambda col: col.astype(str).str.strip())
            #Handle numeric column
            numeric_cols = [columns.get("money_out"), columns.get("money_in"), columns.get("balance")]
            def clean_numeric(col):
                col = col.str.strip().str.replace("'", '', regex=False)
                col = col.str.replace(",", "", regex=False)
                return pd.to_numeric(col, errors='coerce').abs()
            dropped_first_row_df.loc[:, numeric_cols] = dropped_first_row_df[numeric_cols].apply(clean_numeric)

            cleaned_df = pd.DataFrame(columns=new_df_cols)
            cleaned_df[new_df_cols] = dropped_first_row_df[old_df_cols]
            cleaned_df[STATUS_COL] = UNRECONCILED
            self.df = cleaned_df
            return cleaned_df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_debits(self) -> pd.DataFrame:
        try:
            filter_key = "Transfer Charge"
            if self.df is None:
                self.df = self.clean_data()
            df = self.df
            mask1 = df['details'].str.contains(filter_key, case=False, na=False)
            mask2 = df['money_out'] > 0
            kcb_money_out = df[mask2 & ~mask1].copy()
            print(kcb_money_out)
            return kcb_money_out
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_credits(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.df = self.clean_data()
            df = self.df
            mask = df['money_in'] >= 1
            kcb_money_in = df[mask].copy()
            kcb_money_in[STATUS_COL] = RECONCILED
            return  kcb_money_in
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_charges(self) -> pd.DataFrame:
        try:
            filter_key = "Transfer Charge"
            if self.df is None:
                self.df = self.clean_data()
            df = self.df
            mask1 = df['details'].str.contains(filter_key, case=False, na=False)
            kcb_charges = df[mask1].copy()
            kcb_charges[STATUS_COL] = RECONCILED
            return kcb_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))



# reconciler = KcbReconciler(FILE_CONFIGS_KCB, KCB_COLUMNS)
# reconciler.read_file()
# reconciler.get_debits()
# reconciler.get_credits()
# reconciler.get_charges()
