from typing import Optional, List, Union

import pandas as pd

from app.exceptions.exceptions import ReadFileException, ColumnValidationException, FileOperationsException
from app.gateways.equity.WorkpayConfigs import WorkpayEquityConfigs, WorkpayMpesaConfigs, WorkpayKcbConfigs


class WorkpayFIle:

    def __init__(self, session_id: str, configs):
        self.session_id = session_id
        self.dataframe: Optional[pd.DataFrame] = None

        self.file_name_prefix = configs.FILE_PREFIX
        self.excel_skip_rows = configs.EXCEL_SKIP_ROWS
        self.csv_skip_rows = configs.CSV_SKIP_ROWS
        self.sheet_name = configs.SHEET_NAME
        self.date_column = configs.DATE_COLUMN
        self.numeric_columns = configs.NUMERIC_COLUMNS
        self.string_columns = configs.STRING_COLUMNS
        self.api_ref_column = configs.API_REFERENCE_COLUMN
        self.status_column = configs.STATUS_COLUMN
        self.remark_column = configs.REMARK_COLUMN
        self.refund_key = configs.REFUND_KEY
        self.refund_filter = configs.REFUND_FILTER
        self.top_up_key = configs.TOP_UP_KEY
        self.required_columns = configs.REQUIRED_COLUMNS
        self.gateway_name = configs.GATEWAY_NAME

    def set_dataframe(self, df: pd.DataFrame):
        self.dataframe = df


    def load_data(self, data_loader=None) -> None:
        if data_loader is None:
            from app.dataLoading.LoadData import LoadData  # import here for decoupling
            data_loader = LoadData()
        try:
            df = data_loader.read_file(
                session_id=self.session_id,
                file_name_prefix =self.file_name_prefix,
                sheet_name=self.sheet_name,
                excel_skip_rows=self.excel_skip_rows,
                csv_skip_rows=self.csv_skip_rows
            )
            if df.empty:
                raise ReadFileException(f"Failed to load data for file starting with '{self.file_name_prefix}'")
            self.set_dataframe(df)
        except ReadFileException as e:
            raise
        except Exception as e:
            raise ReadFileException(f"Unexpected error loading file starting with '{self.file_name_prefix}'") from e


    def normalize_data(self):
        if self.dataframe is None:
            self.load_data()
        self.validate_columns()
        self.dataframe = self.slice_columns(start_index=0)
        self.handle_date_columns()
        self.handle_numerics()
        self.handle_string_columns()
        self.handle_api_ref_column()
        return self.dataframe

    def get_workpay_equity_top_ups(self) -> pd.DataFrame:
        if self.gateway_name != "workpay_equity":
            return
        if self.dataframe is None:
            self.normalize_data()
        try:
            df = self.dataframe
            remark_series = df[self.remark_column].astype(str)
            mask = remark_series.str.contains(self.top_up_key, case=False, na=False)
            return df.loc[mask].copy()
        except KeyError as e:
            raise FileOperationsException(f"Invalid column: {e}")
        except Exception:
            raise


    def get_workpay_equity_refunds(self) -> pd.DataFrame:
        if self.dataframe is None:
            self.normalize_data()
        try:
            status_series = self.dataframe[self.status_column].astype(str)
            remark_series = self.dataframe[self.remark_column].astype(str)
            mask = (
                    remark_series.str.contains(self.refund_filter, case=False, na=False) |
                    status_series.str.contains(self.refund_key, case=False, na=False)
            )
            return self.dataframe.loc[mask].copy()
        except KeyError as e:
            raise FileOperationsException(f"Invalid column: {e}")
        except Exception:
            raise


    def get_workpay_equity_payouts(self) -> pd.DataFrame:
        if self.dataframe is None:
            self.normalize_data()
        try:
            status_series = self.dataframe[self.status_column]
            remark_series = self.dataframe[self.remark_column]
            mask = (
                    ~remark_series.isin([self.refund_filter, self.top_up_key]) &
                    ~status_series.str.contains(self.refund_key, case=False, na=False)
            )
            return self.dataframe.loc[mask].copy()
        except KeyError as e:
            raise FileOperationsException(f"Invalid column: {e}")
        except Exception:
            raise


    def handle_api_ref_column(self) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        self.dataframe[self.api_ref_column] = self.dataframe[self.api_ref_column].astype(str).str.replace(".0", "")
        return self.dataframe


    def handle_string_columns(self) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        null_like_values = {"", "none", "null", "nan"}
        for col in self.string_columns:
            if col not in self.dataframe.columns:
                raise ValueError(f"String column '{col}' not found in DataFrame")
            self.dataframe[col] = (
                self.dataframe[col]
                .astype(str)
                .str.strip()
            )
            self.dataframe[col] = self.dataframe[col].where(
                ~self.dataframe[col].isin(null_like_values),
                other="NA"
            )
        return self.dataframe


    def handle_numerics(self) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        for col in self.numeric_columns:
            if col not in self.dataframe.columns:
                raise ValueError(f"Column '{col}' not found in DataFrame")
            self.dataframe[col] = self.dataframe[col].astype(str).str.strip()
            self.dataframe[col] = self.dataframe[col].replace("", "0")
            self.dataframe[col] = (
                self.dataframe[col]
                .str.replace(r"[^\d\.-]", "", regex=True)
                .str.replace(r"^-*(?=\d)", "", regex=True)
            )
            self.dataframe[col] = pd.to_numeric(self.dataframe[col], errors="coerce").abs().fillna(0)
        return self.dataframe


    def handle_date_columns(self, date_format: str = "%Y-%m-%d %H:%M:%S") -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        if self.date_column not in self.dataframe.columns:
            raise ValueError(f"Required date column '{self.date_column}' not found in DataFrame.")
        self.dataframe[self.date_column] = pd.to_datetime(self.dataframe[self.date_column], format=date_format, errors="coerce")
        return self.dataframe


    def slice_columns(self, start_index: int = 0, end_index: Optional[int] = None) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        dataframe = self.dataframe.iloc[:-1].copy()
        if end_index is None:
            end_index = dataframe.shape[1]
        return dataframe.iloc[:, start_index:end_index]


    def validate_columns(self) -> None:
        if self.dataframe is None:
            raise ColumnValidationException("DataFrame is not loaded. Call `load_data()` first.")
        missing_columns: List[str] = [
            col for col in self.required_columns if col not in self.dataframe.columns
        ]
        if missing_columns:
            raise ColumnValidationException(
                f"The following required columns are missing in '{self.file_name_prefix}': {missing_columns}"
            )



# wp_file = WorkpayFIle( "sess:2025-11-21_06:29:47", WorkpayKcbConfigs)
# debits = wp_file.get_workpay_equity_payouts()
# refunds = wp_file.get_workpay_equity_refunds()
# topUps = wp_file.get_workpay_equity_top_ups()
# print(debits)