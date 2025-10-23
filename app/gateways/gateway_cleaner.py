import datetime
import re
from typing import List, final
import pandas as pd

from app.exceptions.exceptions import NullValueException, EmptyDataException
from app.utils.constants import *
from app.utils.read_recon_files import read_file

STATUS_COL = 'status'
DATE_COL = 'date'
UNNAMED_COLS= ['Unnamed: 0', 'Unnamed: 1']

EQUITY_GATEWAY = "equity"
KCB_GATEWAY = "kcb"
MMF_GATEWAY = "mmf"
UTILITY_GATEWAY = "utility"

CHARGES_FILTER_KEYS = ["JENGA CHARGE", " Transfer Charge", "Business Pay Bill Charge",
                       "Business Buy Goods Charge", "B2C Payment Charge"]

class GatewayCleaner:

    def __init__(self, configs, columns):
        self.configs = configs
        self.columns = columns
        self.df = None


    def __drop_bottom_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        dataframe = df.copy()
        empty_rows = dataframe.isnull().all(axis=1)
        first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(dataframe)
        if empty_rows.any():
            return dataframe.loc[:first_empty_idx - 1]
        else:
            return dataframe


    def __drop_unnamed_columns(self, df: pd.DataFrame, columns: List[str]):
        dataframe = df.copy()
        exists_unnamed_cols = any(col in columns for col in df.columns)
        new_dataframe = dataframe.drop(columns=columns) if exists_unnamed_cols else dataframe
        final_dataframe = self.__drop_bottom_rows(new_dataframe)
        return final_dataframe


    def __assign_date_column(self, df: pd.DataFrame, trn_date: str, value_date: str, new_date: str, date_format: str):
        dataframe = df.copy()
        dataframe[new_date] = datetime.date.today()
        if trn_date not in dataframe.columns:
            dataframe[new_date] = dataframe[value_date]
        else:
            dataframe[new_date] = dataframe[trn_date]
        dataframe[new_date] = (dataframe[new_date].astype(str).str.strip().apply(pd.to_datetime, errors='coerce', format=date_format))
        return dataframe


    def __handle_numerics_columns(self, df: pd.DataFrame, columns: List):
        dataframe = df.copy()
        def clean_numeric(col):
            col = col.astype(str).str.strip().str.replace("'", "", regex=False)
            col = col.str.replace(",", "", regex=False)
            return pd.to_numeric(col, errors='coerce').fillna(0).abs()
        dataframe.loc[:, columns] = dataframe[columns].apply(clean_numeric)
        return dataframe


    def __drop_first_row(self, df: pd.DataFrame):
        dataframe = df.copy()
        dataframe= dataframe.iloc[1:].copy()
        return dataframe


    def __handle_reference_column(self, df: pd.DataFrame, ref_column: str, fill_column:str):
        dataframe = df.copy()
        if ref_column not in df.columns:
            dataframe[ref_column] = dataframe[fill_column]
        return  dataframe


    def get_data(self) -> pd.DataFrame:
        self.df = read_file(filename_prefix=self.configs.get("prefix"), sheet_name=self.configs.get("sheet_name"),
                                    excel_skip_rows=self.configs.get("excel_rows"), csv_skip_rows=self.configs.get("csv_rows"))
        if self.df.empty:
            raise EmptyDataException(message=f"Failed to get data for {self.configs.get('name')} gateway")
        return self.df


    def clean_data(self) -> pd.DataFrame:
        transaction_date = self.columns.get("transaction_date")
        value_date = self.columns.get("value_date")
        reference_column = self.columns.get("reference")
        details_column = self.columns.get("details")
        new_date = "date"
        numeric_cols = [self.columns.get(col) for col in ['debits', 'credits']]
        new_df_cols = ["date", "details", "reference", "debits", "credits"]
        old_df_cols = [self.columns.get(col) for col in new_df_cols]

        if self.df is None:
            self.get_data()
        dataframe = self.df
        #if gateway is equity bank drop first two empty columns
        if self.configs.get("name").lower() == EQUITY_GATEWAY:
            dataframe = self.__drop_unnamed_columns(dataframe, UNNAMED_COLS)
            dataframe = self.__handle_reference_column(dataframe, reference_column, details_column)
        #if gateway is kcb bank drop first row
        if self.configs.get("name").lower() == KCB_GATEWAY:
            dataframe = self.__drop_first_row(dataframe)
        #Assign a date columns
        if self.configs.get("name") in [MMF_GATEWAY, UTILITY_GATEWAY]:
            dataframe = self.__assign_date_column(dataframe, transaction_date, value_date, new_date, "%d-%m-%Y %H:%M:%S")
        elif self.configs.get("name") == KCB_GATEWAY:
            dataframe = self.__assign_date_column(dataframe, transaction_date, value_date, new_date, "%d.%m.%Y")
        else:
            dataframe = self.__assign_date_column(dataframe, transaction_date, value_date, new_date, "%d-%m-%Y")
        #Handle numerics
        dataframe = self.__handle_numerics_columns(dataframe, numeric_cols)
        #create new dataframe
        final_dataframe = pd.DataFrame(columns=new_df_cols)
        final_dataframe[new_df_cols] = dataframe[old_df_cols]
        final_dataframe[STATUS_COL] = UNRECONCILED
        if final_dataframe.empty:
            raise EmptyDataException(message=f"Failed to clean data for {self.configs.get('name')} gateway")
        self.df = final_dataframe
        return final_dataframe


    def get_debits(self) -> pd.DataFrame:
        if self.df is None:
            self.df = self.clean_data()
        dataframe = self.df
        mask = dataframe['details'].str.contains('|'.join(map(re.escape, CHARGES_FILTER_KEYS)), case=False, na=False)
        mask1 = dataframe['debits'] >= 1
        debits_dataframe = dataframe[~mask & mask1]
        return debits_dataframe


    def get_credits(self) -> pd.DataFrame:
        if self.df is None:
            self.df = self.clean_data()
        dataframe = self.df
        mask = dataframe['credits'] >= 1
        credits_dataframe = dataframe[mask]
        credits_dataframe.loc[:, STATUS_COL] = RECONCILED
        return credits_dataframe


    def get_charges(self) -> pd.DataFrame:
        if self.df is None:
            self.df = self.clean_data()
        dataframe = self.df
        mask = dataframe['details'].str.contains('|'.join(map(re.escape, CHARGES_FILTER_KEYS)), case=False, na=False)
        mask1 = dataframe['credits'] == 0
        charges_dataframe = dataframe[mask & mask1]
        charges_dataframe.loc[:, STATUS_COL] = RECONCILED
        return charges_dataframe
