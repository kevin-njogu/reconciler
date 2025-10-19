import re
import uuid
import pandas as pd
from fastapi import HTTPException

from app.utils.constants import UNRECONCILED, RECONCILED
from app.utils.read_recon_files import read_file


STATUS_COL = "status"

class MpesaReconciler:
    def __init__(self, configs, columns, file_prefix):
        self.configs = configs
        self.columns = columns
        self.file_prefix = file_prefix
        self.df = None


    def read_file(self) -> pd.DataFrame:
        try:
            configs = self.configs
            self.df= read_file(filename_prefix=self.file_prefix, sheet_name=configs.get("sheet_name"),
                              excel_skip_rows=configs.get("excel_rows"), csv_skip_rows=configs.get("csv_rows"))
            return self.df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self) -> pd.DataFrame:
        try:
            columns = self.columns
            new_df_cols = ["date", "transaction_id", "details", "paid_in", "withdrawn"]
            old_df_cols = [columns.get(k) for k in ["completion_time", "receipt_no", "details", "paid_in", "withdrawn"]]

            if self.df is None:
                self.read_file()
            raw_df = self.df

            date_cols = [columns.get("completion_time"), columns.get("initiation_time")]
            raw_df.loc[:, date_cols] = raw_df[date_cols].apply(pd.to_datetime, errors='coerce', format="%d-%m-%Y %H:%M:%S")

            raw_df.loc[:, columns.get("receipt_no")] = raw_df[columns.get("receipt_no")].apply(
                lambda x: f"{self.file_prefix}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str)

            str_cols = [columns.get("details")]
            raw_df.loc[:, str_cols] = raw_df[str_cols].astype('string').fillna("NA").apply(lambda col: col.astype(str).str.strip())

            numeric_cols = [columns.get("paid_in"), columns.get("withdrawn")]
            raw_df[numeric_cols] = (raw_df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0).abs())

            mpesa_cleaned = pd.DataFrame(columns=new_df_cols)
            mpesa_cleaned[new_df_cols] = raw_df[old_df_cols]
            mpesa_cleaned[STATUS_COL] = UNRECONCILED
            self.df = mpesa_cleaned
            return mpesa_cleaned
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_paid_outs(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.clean_data()
            df = self.df
            filter_str = ["Business Pay Bill Charge", "Business Buy Goods Charge", "B2C Payment Charge"]
            mask_charges = df['details'].str.contains('|'.join(map(re.escape, filter_str)), case=False, na=False)
            mask_paid_in = df['paid_in'] > 0
            mpesa_payouts = df[~mask_paid_in & ~mask_charges].copy()
            return mpesa_payouts
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_charges(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.clean_data()
            df = self.df
            filter_str_one = "Business Pay Bill Charge"
            filter_str_two = "Business Buy Goods Charge"
            filter_str_three = "B2C Payment Charge"
            mask1 = df['details'].str.contains(filter_str_one, case=False, na=False)
            mask2 = df['details'].str.contains(filter_str_two, case=False, na=False)
            mask3 = df['details'].str.contains(filter_str_three, case=False, na=False)
            main_mask = mask1 | mask2 | mask3
            mpesa_charges = df[main_mask].copy()
            mpesa_charges[STATUS_COL] = RECONCILED
            return mpesa_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_paid_ins(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.clean_data()
            df = self.df
            mask1 = df['paid_in'] > 0
            mpesa_paid_in = df[mask1].copy()
            mpesa_paid_in[STATUS_COL] = RECONCILED
            print(mpesa_paid_in)
            return mpesa_paid_in
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


class MpesaMmf(MpesaReconciler):
    def __init__(self, configs, columns, file_prefix):
        super().__init__(configs, columns, file_prefix)


class MpesaUtility(MpesaReconciler):
    def __init__(self, configs, columns, file_prefix):
        super().__init__(configs, columns, file_prefix)

