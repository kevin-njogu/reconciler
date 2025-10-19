import uuid
from fastapi import HTTPException
import pandas as pd
from app.utils.constants import UNRECONCILED
from app.utils.read_recon_files import read_file


TOP_UP_KEY = 'Account Top Up'
TOP_UP_FILL_KEY = 'WALLET TOPUP'
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
            top_up_mask = dropped_last_row_df[columns.get('remark')] ==  TOP_UP_KEY
            dropped_last_row_df.loc[top_up_mask, columns.get('ref')] = TOP_UP_FILL_KEY
            refund_mask_one = dropped_last_row_df[columns.get('processing_status')] == "refunded"
            refund_mask_two = dropped_last_row_df[columns.get('remark')].str.contains("Refund")
            refund_mask = refund_mask_one | refund_mask_two
            dropped_last_row_df.loc[refund_mask, columns.get('ref')] = REFUND_FILL_KEY
            #Handle numeric columns
            numeric_cols = [columns.get('amount'), columns.get('sender_fee'), columns.get("recipient_fee")]
            dropped_last_row_df.loc[:, numeric_cols] = dropped_last_row_df[numeric_cols].apply(pd.to_numeric, errors='coerce')

            wp_equity_df = pd.DataFrame(columns=new_df_cols)
            wp_equity_df[new_df_cols] = dropped_last_row_df[old_df_cols]
            wp_equity_df[STATUS_COL] = UNRECONCILED
            self.df = wp_equity_df
            return wp_equity_df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_payouts(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_equity_payouts = df.loc[~df['api_reference'].isin([REFUND_FILL_KEY, TOP_UP_FILL_KEY])]
        return wp_equity_payouts


    def get_refunds(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_equity_refunds = df.loc[df['api_reference'] == REFUND_FILL_KEY]
        return wp_equity_refunds


    def get_top_ups(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_equity_top_ups = df.loc[df['api_reference'] == TOP_UP_FILL_KEY]
        return wp_equity_top_ups


# df = read_workpay_file(FILE_CONFIGS)
# clean_df = clean_data(df, WP_EQUITY_COLS)
# get_top_ups(clean_df)

