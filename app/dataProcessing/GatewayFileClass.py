import re
from typing import Optional, List, Union

import pandas as pd

from app.exceptions.exceptions import ReadFileException, ColumnValidationException, FileOperationsException


class GatewayFile:

    def __init__(self, session_id: str, configs):
        self.session_id = session_id
        self.dataframe: Optional[pd.DataFrame] = None

        self.file_name_prefix = configs.FILE_PREFIX
        self.excel_skip_rows = configs.BANK_EXCEL_SKIP_ROWS
        self.csv_skip_rows = configs.BANK_CSV_SKIP_ROWS
        self.sheet_name: Union[str|int] = configs.BANK_SHEET_NAME
        self.date_column = configs.DATE_COLUMN
        self.numeric_columns = configs.NUMERIC_COLUMNS
        self.string_columns = configs.STRING_COLUMNS
        self.narrative_column = configs.NARRATIVE_COLUMN
        self.debit_column = configs.DEBIT_COLUMN
        self.credit_column = configs.CREDIT_COLUMN
        self.required_columns = configs.REQUIRED_COLUMNS
        self.date_format = configs.DATE_FORMAT
        self.gateway_name = configs.GATEWAY_NAME
        self.charges_filters = configs.CHARGES_FILTER_KEY
        self.mpesa_prefixes = configs.MPESA_PREFIXES


    def set_dataframe(self, df: pd.DataFrame):
        self.dataframe = df


    def load_data(self, data_loader=None) -> None:
        df = pd.DataFrame()
        if data_loader is None:
            from app.dataLoading.read import LoadData  # import here for decoupling
            data_loader = LoadData()
        try:
            if self.gateway_name == "mpesa":
                dataframes = []
                for prefix in self.mpesa_prefixes:
                    try:
                        df = data_loader.read_file(
                            session_id=self.session_id,
                            file_name_prefix=prefix,
                            sheet_name=self.sheet_name,
                            excel_skip_rows=self.excel_skip_rows,
                            csv_skip_rows=self.csv_skip_rows
                        )
                        if df is not None and not df.empty:
                            dataframes.append(df)
                    except ReadFileException:
                        raise
                df = pd.concat(dataframes, ignore_index=True)
            else:
                df = data_loader.read_file(
                    session_id=self.session_id,
                    file_name_prefix =self.file_name_prefix,
                    sheet_name=self.sheet_name,
                    excel_skip_rows=self.excel_skip_rows,
                    csv_skip_rows=self.csv_skip_rows)
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

        if self.gateway_name == "equity":
            self.slice_columns(start_index=2)
            self.drop_bottom_rows()

        self.handle_date_columns()
        self.handle_numerics()
        self.handle_string_columns()
        return self.dataframe


    def get_equity_charges(self) -> pd.DataFrame:
        if self.dataframe is None:
            self.normalize_data()
        required_cols = [self.narrative_column, self.debit_column, self.credit_column]
        missing = [col for col in required_cols if col not in self.dataframe.columns]
        if missing:
            raise FileOperationsException(f"Missing required columns: {missing}")
        try:
            regex_pattern = "|".join(map(re.escape, self.charges_filters))
            narrative_series = self.dataframe[self.narrative_column].astype(str)
            mask_charges = narrative_series.str.contains(
                regex_pattern, case=False, na=False
            )
            debit_series = pd.to_numeric(self.dataframe[self.debit_column], errors="coerce").fillna(0)
            mask_debits = debit_series > 0

            charges_df = self.dataframe.loc[mask_charges & mask_debits].copy()
            charges_df["Remarks"] = "CHARGE"
            return charges_df
        except KeyError as e:
            raise FileOperationsException(f"Invalid column: {e}") from e
        except Exception as e:
            raise FileOperationsException("Error while extracting charge entries") from e


    def get_equity_credits(self) -> pd.DataFrame:
        try:
            if self.dataframe is None:
                self.normalize_data()
            if self.credit_column not in self.dataframe.columns:
                raise FileOperationsException(
                    f"Missing required column '{self.credit_column}'"
                )
            credit_series = pd.to_numeric(
                self.dataframe[self.credit_column], errors="coerce"
            ).fillna(0)
            mask = credit_series >= 1
            credits_df = self.dataframe.loc[mask].copy()
            credits_df["Remarks"] = "DEPOSIT"
            return credits_df
        except KeyError as e:
            raise FileOperationsException(f"Invalid column: {e}") from e
        except Exception as e:
            raise FileOperationsException("Error extracting credit transactions") from e


    def get_equity_debits(self) -> pd.DataFrame:
        if self.dataframe is None:
            self.normalize_data()
        required_cols = [self.narrative_column, self.debit_column]
        missing = [col for col in required_cols if col not in self.dataframe.columns]
        if missing:
            raise FileOperationsException(f"Missing required columns: {missing}")
        try:
            regex_pattern = "|".join(map(re.escape, self.charges_filters))
            narrative_series = self.dataframe[self.narrative_column].astype(str)
            mask_charges = narrative_series.str.contains(regex_pattern, case=False, na=False)
            mask_debits = self.dataframe[self.debit_column].fillna(0) >= 1
            return self.dataframe.loc[~mask_charges & mask_debits].copy()
        except KeyError as e:
            raise FileOperationsException(f"Invalid column encountered: {e}") from e
        except Exception as e:
            raise FileOperationsException("Error while extracting debit transactions") from e


    def drop_bottom_rows(self, target_string: str = "----- End of Statement -----") -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        mask = self.dataframe.astype(str).apply(lambda col: col.str.contains(target_string, case=False, na=False))
        row_mask = mask.any(axis=1)
        if row_mask.any():
            first_match_idx = row_mask.idxmax()
            self.dataframe = self.dataframe.loc[:first_match_idx - 1]
        return self.dataframe


    def handle_string_columns(self) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        null_like_values = {"", "none", "null", "nan"}
        for col in self.string_columns:
            if col not in self.dataframe.columns:
                raise ValueError(f"String column '{col}' not found in DataFrame")
            self.dataframe[col] = (
                self.dataframe[col].astype(str).str.strip())
            self.dataframe[col] = self.dataframe[col].where(~self.dataframe[col].isin(null_like_values),other="NA")
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


    def handle_date_columns(self) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        if self.date_column not in self.dataframe.columns:
            raise ValueError(f"Required date column '{self.date_column}' not found in DataFrame.")
        self.dataframe[self.date_column] = pd.to_datetime(self.dataframe[self.date_column], format=self.date_format, errors="coerce")
        return self.dataframe


    def slice_columns(self, start_index: int = 0, end_index: Optional[int] = None) -> pd.DataFrame:
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded. Call `load_data()` first.")
        num_columns = self.dataframe.shape[1]
        if start_index >= num_columns:
            raise ValueError(f"Cannot slice starting at index {start_index}. DataFrame has only {num_columns} columns.")
        end_index = end_index if end_index is not None else num_columns
        self.dataframe = self.dataframe.iloc[:, start_index:end_index]
        return self.dataframe


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


#eq_file = GatewayFile( "sess:2025-11-21_06:29:47", EquityConfigs)
# eq_file.load_data()
# eq_file.normalize_data()
# debits = eq_file.get_equity_debits()
# credits = eq_file.get_equity_credits()
# charges =  eq_file.get_equity_charges()
# print(charges)

# kcb_file = GatewayFile("sess:2025-11-21_06:29:47", KcbConfigs)
# eq_file.load_data()
# eq_file.normalize_data()
# debits = kcb_file.get_equity_debits()
# credits = kcb_file.get_equity_credits()
# charges =  kcb_file.get_equity_charges()
# print(credits)

# utility_file = GatewayFile("sess:2025-11-21_06:29:47", UtilityConfigs)
# debits = utility_file.get_equity_debits()
# credits = utility_file.get_equity_credits()
# charges =  utility_file.get_equity_charges()
# print(charges)

# mmf_file = GatewayFile("sess:2025-11-21_06:29:47", MmfConfigs)
# debits = mmf_file.get_equity_debits()
# credits = mmf_file.get_equity_credits()
# charges =  mmf_file.get_equity_charges()
# print(charges)

# mpesa_file = GatewayFile("sess:2025-11-21_06:29:47", MpesaConfigs)
# debits = mpesa_file.get_equity_debits()
# credits = mpesa_file.get_equity_credits()
# charges =  mpesa_file.get_equity_charges()
# print(debits)
