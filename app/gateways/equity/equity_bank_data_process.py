import datetime
from typing import List
import pandas as pd
from fastapi import HTTPException
from app.utils.constants import UNRECONCILED, RECONCILED
from app.utils.read_recon_files import read_file

STATUS_COL = 'status'

class EquityReconciler:

    def __init__(self, configs):
        self.configs = configs
        self.df = None


    def drop_bottom_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        empty_rows = df.isnull().all(axis=1)
        first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(df)
        if empty_rows.any():
            return df.loc[:first_empty_idx - 1]
        else:
            return df


    def handle_date(self, df: pd.DataFrame, trn_date: str, value_date: str, new_date: str):
        df[new_date] = datetime.date.today()
        if trn_date not in df.columns:
            df[new_date] = df[value_date]
        else:
            df[new_date] = df[trn_date]
        df[new_date] = (df[new_date].astype(str).str.strip().apply(pd.to_datetime, errors='coerce', format="%d-%m-%Y"))
        return df


    def handle_numerics(self, df: pd.DataFrame, columns: List):
        for col in columns:
            df[col] = (df[col].astype(str).str.strip().apply(pd.to_numeric, errors='coerce').fillna(0))
        return df


    def read_equity_bank_file(self) -> pd.DataFrame:
        try:
            self.df = read_file(filename_prefix=self.configs.get("prefix"), sheet_name=self.configs.get("sheet_name"),
                                        excel_skip_rows=self.configs.get("excel_rows"),csv_skip_rows=self.configs.get("csv_rows"))
            return self.df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.read_equity_bank_file()
            df = self.df

            trn_date = "Transaction Date"
            value_date = "Value Date"
            new_date = "Date"
            equity_df = pd.DataFrame()
            unnamed_cols = ['Unnamed: 0', 'Unnamed: 1']
            numeric_cols = ['Debit', 'Credit']
            old_df_cols = ["Date", "Narrative", "Debit", "Credit"]
            new_df_cols = ["date", "narrative", "debit", "credit"]

            # drop first two empty columns if they exist
            exists_unnamed_cols = any(col in unnamed_cols for col in df.columns)
            if exists_unnamed_cols:
                equity_df = df.drop(columns=unnamed_cols).copy()
            #Drop the bottom un-necessary rows
            dropped_last_rows_df = self.drop_bottom_rows(equity_df).copy()
            #Handle dates
            aligned_dates_df = self.handle_date(dropped_last_rows_df, trn_date, value_date, new_date)
            #Handle numerics
            final_raw_df = self.handle_numerics(aligned_dates_df, numeric_cols)

            final_dataframe = pd.DataFrame(columns=new_df_cols)
            final_dataframe[new_df_cols] = final_raw_df[old_df_cols]
            final_dataframe[STATUS_COL] = UNRECONCILED
            self.df = final_dataframe
            return final_dataframe
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_debits(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.df = self.clean_data()
            equity_df = self.df
            filter_key = 'CHARGE'
            mask = equity_df['narrative'].str.contains(filter_key, case=False, na=False)
            mask1 = equity_df['debit'] >= 1
            equity_bank_debits = equity_df[~mask & mask1].copy()
            return equity_bank_debits
        except Exception as e:
            raise HTTPException(status_code=500, detail=e)


    def get_credits(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.df = self.clean_data()
            equity_df = self.df
            mask = equity_df['credit'] >= 1
            equity_bank_credits = equity_df[mask].copy()
            equity_bank_credits[STATUS_COL] = RECONCILED
            return equity_bank_credits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_charges(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.df = self.clean_data()
            equity_df = self.df
            filter_key = 'JENGA CHARGE'
            mask = equity_df['narrative'].str.contains(filter_key, case=False, na=False)
            mask1 = equity_df['credit'] == 0
            equity_bank_charges = equity_df[mask & mask1].copy()
            equity_bank_charges[STATUS_COL] = RECONCILED
            return equity_bank_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


# df = read_equity_bank_file(FILE_CONFIGS)
# clean_df = clean_data(df)
# get_charges(clean_df)
