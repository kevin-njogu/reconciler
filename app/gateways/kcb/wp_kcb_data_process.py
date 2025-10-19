import uuid
from fastapi import HTTPException
import pandas as pd

from app.gateways.equity.services import reconcile
from app.utils.constants import UNRECONCILED, RECONCILED, FILE_CONFIGS_KCB, FILE_CONFIGS_WORKPAY_KCB, WP_COLS
from app.utils.read_recon_files import read_file



REFUND_FILL_KEY = 'REFUND'
STATUS_COL = 'status'

class WorkpayReconciler:

    def __init__(self, configs, columns):
        self.configs = configs
        self.columns = columns
        self.df = None

    def read_workpay_file(self) -> pd.DataFrame:
        try:
            self.df= read_file(filename_prefix=self.configs.get("prefix"), sheet_name=self.configs.get("sheet_name"),
                                        excel_skip_rows=self.configs.get("excel_rows"),csv_skip_rows=self.configs.get("csv_rows"))
            return self.df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self) -> pd.DataFrame:
        try:
            if self.df is None:
                self.read_workpay_file()
            df = self.df
            columns = self.columns
            configs = self.configs
            new_df_cols = ['date', "transaction_id", "api_reference", "recipient", "amount", "sender_fee", "recipient_fee"]
            old_df_cols = [columns.get(k) for k in ['date', 'tid', 'ref', 'recipient', 'amount', 'sender_fee', 'recipient_fee']]

            dropped_last_row_df = df.iloc[:-1].copy()
            #Handle date column
            dropped_last_row_df.loc[:, columns.get('date')] = (dropped_last_row_df[columns.get('date')].astype(str).str.split(" ").str[0])
            dropped_last_row_df.loc[:, columns.get('date')] = (dropped_last_row_df[columns.get('date')].apply(pd.to_datetime, errors="coerce"))
            #Handle transaction Id column
            dropped_last_row_df.loc[:, columns.get('tid')] = dropped_last_row_df[columns.get('tid')].apply(
                lambda x: f"{configs.get('prefix')}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str)
            # #Align equity api refs
            dropped_last_row_df[columns.get('ref')] = (dropped_last_row_df[columns.get('ref')].astype(str).str.split(".").str[0])
            refund_mask_one = dropped_last_row_df[columns.get('processing_status')] == "refunded"
            refund_mask_two = dropped_last_row_df[columns.get('remark')].str.contains("Refund")
            refund_mask = refund_mask_one | refund_mask_two
            dropped_last_row_df.loc[refund_mask, columns.get('ref')] = REFUND_FILL_KEY
            #Handle numeric columns
            numeric_cols = [columns.get('amount'), columns.get('sender_fee'), columns.get("recipient_fee")]
            dropped_last_row_df.loc[:, numeric_cols] = dropped_last_row_df[numeric_cols].apply(pd.to_numeric, errors='coerce')

            cleaned_df= pd.DataFrame(columns=new_df_cols)
            cleaned_df[new_df_cols] = dropped_last_row_df[old_df_cols]
            cleaned_df[STATUS_COL] = UNRECONCILED
            self.df = cleaned_df
            return cleaned_df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_payouts(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        payouts_df = df.loc[~df['api_reference'].isin([REFUND_FILL_KEY])]
        return payouts_df


    def get_refunds(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        mask = df['api_reference']==REFUND_FILL_KEY
        refunds_df = df[mask]
        refunds_df[STATUS_COL] = RECONCILED
        print(refunds_df)
        return refunds_df


# reconciler = WorkpayReconciler(FILE_CONFIGS_WORKPAY_KCB, WP_COLS)
# reconciler.read_workpay_file()
# reconciler.clean_data()
# reconciler.get_payouts()
# reconciler.get_refunds()

