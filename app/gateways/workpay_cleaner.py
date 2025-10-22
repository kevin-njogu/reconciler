import uuid
from typing import List

from fastapi import HTTPException
import pandas as pd
from rich_toolkit.utils.colors import darken

from app.exceptions.exceptions import EmptyDataException
from app.utils.constants import *
from app.utils.read_recon_files import read_file


TOP_UP_KEY = 'Account Top Up'
TOP_UP_FILL_KEY = 'WALLET TOPUP'
REFUND_FILL_KEY = 'REFUND'
STATUS_COL = 'status'

MPESA_GATEWAY = "mpesa"
EQUITY_GATEWAY = "equity"

class WorkpayCleaner:

    def __init__(self, configs, columns, name):
        self.configs = configs
        self.columns = columns
        self.name = name
        self.df = None


    def __handle_dates(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        dataframe = df.copy()
        # dataframe.loc[:, date_col] = (dataframe[date_col].astype(str).str.split(" ").str[0])
        dataframe.loc[:, date_col] = (dataframe[date_col].apply(pd.to_datetime, errors="coerce"))
        return dataframe

    def __handle_transaction_id(self, df:pd.DataFrame, tid_col:str) -> pd.DataFrame:
        dataframe = df.copy()
        dataframe.loc[:, tid_col] = dataframe[tid_col].apply(
            lambda x: f"{self.configs.get('prefix')}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str)
        return dataframe

    def __handle_mpesa_tid(self, df:pd.DataFrame, tid_col: str) -> pd.DataFrame:
        dataframe = df.copy()
        mask_reversal = dataframe[tid_col].str.contains('000000')
        dataframe.loc[mask_reversal, tid_col] = (dataframe.loc[mask_reversal, tid_col].apply(
            lambda x: f"{x}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str))
        return dataframe

    def __handle_top_ups(self, df: pd.DataFrame, remarks_col: str, ref_col: str) -> pd.DataFrame:
        dataframe = df.copy()
        top_up_mask = dataframe[remarks_col] == TOP_UP_KEY
        dataframe[ref_col] = dataframe[ref_col].astype(str)
        dataframe.loc[top_up_mask, ref_col] = TOP_UP_FILL_KEY
        return dataframe

    def __handle_equity_refs(self, df: pd.DataFrame, ref_col: str):
        dataframe = df.copy()
        dataframe[ref_col] = (dataframe[ref_col].astype(str).str.split(".").str[0])
        return dataframe

    def __handle_null_refs(self, df: pd.DataFrame, ref_col: str) -> pd.DataFrame:
        dataframe = df.copy()
        dataframe[ref_col] = dataframe[ref_col].astype(str).apply(
            lambda x: f"{self.configs.get('prefix')}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str)
        return dataframe

    def __handle_refunds(self, df: pd.DataFrame, processing_status_col: str, remarks_col: str, ref_col: str) -> pd.DataFrame:
        dataframe = df.copy()
        refund_mask_one = dataframe[processing_status_col] == "refunded"
        refund_mask_two = dataframe[remarks_col].str.contains("Refund")
        refund_mask = refund_mask_one | refund_mask_two
        dataframe.loc[refund_mask, ref_col] = REFUND_FILL_KEY
        return dataframe

    def __handle_numeric_cols(self, df: pd.DataFrame, numeric_cols: List[str]):
        dataframe = df.copy()
        dataframe.loc[:, numeric_cols] = dataframe[numeric_cols].apply(pd.to_numeric, errors='coerce')
        return dataframe

    def get_data(self) -> pd.DataFrame:
        try:
            self.df= read_file(filename_prefix=self.configs.get("prefix"), sheet_name=self.configs.get("sheet_name"),
                                        excel_skip_rows=self.configs.get("excel_rows"),csv_skip_rows=self.configs.get("csv_rows"))
            if self.df.empty:
                raise EmptyDataException(message=f"Failed to get workpay data for {self.name} gateway")
            return self.df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self) -> pd.DataFrame:
        try:
            numeric_cols = [self.columns.get('amount'), self.columns.get('sender_fee'), self.columns.get("recipient_fee")]
            new_df_cols = ['date', "transaction_id", "api_reference", "recipient", "amount", "sender_fee", "recipient_fee"]
            old_df_cols = [self.columns.get(k) for k in ['date', 'tid', 'ref', 'recipient', 'amount', 'sender_fee', 'recipient_fee']]

            if self.df is None:
                self.get_data()
            dataframe = self.df

            dataframe = dataframe.iloc[:-1].copy()
            #Handle date column
            dataframe = self.__handle_dates(dataframe, self.columns.get('date'))
            #Handle transaction Id column
            dataframe = self.__handle_transaction_id(dataframe, self.columns.get('tid'))
            #Handle tid if mpesa
            if self.name.lower() == MPESA_GATEWAY:
                dataframe = self.__handle_mpesa_tid(dataframe, self.columns.get('tid'))
            #Handle top-ups if equity
            if self.name.lower() == EQUITY_GATEWAY:
                dataframe = self.__handle_top_ups(dataframe, self.columns.get('remark'), self.columns.get('ref'))
                dataframe = self.__handle_equity_refs(dataframe, self.columns.get('ref'))
            #Handle null refs
            dataframe = self.__handle_null_refs(dataframe, self.columns.get('ref'))
            #handle refunds
            dataframe = self.__handle_refunds(dataframe, self.columns.get('processing_status'), self.columns.get('remark'), self.columns.get('ref'))
            #Handle numeric columns
            dataframe = self.__handle_numeric_cols(dataframe, numeric_cols)
            #Create a clean dataframe
            cleaned_dataframe = pd.DataFrame(columns=new_df_cols)
            cleaned_dataframe[new_df_cols] =  dataframe[old_df_cols]
            cleaned_dataframe[STATUS_COL] = UNRECONCILED
            if cleaned_dataframe.empty:
                raise EmptyDataException(message=f"Failed to clean workpay data for {self.name} gateway")
            self.df = cleaned_dataframe
            return cleaned_dataframe
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def get_payouts(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_payouts = df.loc[~df['api_reference'].isin([REFUND_FILL_KEY, TOP_UP_FILL_KEY])]
        return wp_payouts


    def get_refunds(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_refunds = df.loc[df['api_reference'] == REFUND_FILL_KEY]
        wp_refunds.loc[:, STATUS_COL] = RECONCILED
        return wp_refunds


    def get_top_ups(self) -> pd.DataFrame:
        if self.df is None:
            self.clean_data()
        df = self.df
        wp_top_ups = df.loc[df['api_reference'] == TOP_UP_FILL_KEY]
        wp_top_ups.loc[:, STATUS_COL] = RECONCILED
        return wp_top_ups
