"""
Gateway File Processing Module.

Handles loading and processing transaction files for reconciliation.
Uses a unified template format with columns: Date, Reference, Details, Debit, Credit.
"""
import re
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, List

import pandas as pd

from app.dataLoading.data_loader import DataLoader
from app.exceptions.exceptions import ReadFileException, ColumnValidationException, FileOperationsException
from app.upload.template_generator import (
    DATE_COLUMN,
    REFERENCE_COLUMN,
    DETAILS_COLUMN,
    DEBIT_COLUMN,
    CREDIT_COLUMN,
    TEMPLATE_COLUMNS,
    TEMPLATE_DATE_FORMAT,
)

# Backwards-compatible aliases
TRANSACTION_ID_COLUMN = REFERENCE_COLUMN
NARRATIVE_COLUMN = DETAILS_COLUMN

logger = logging.getLogger("app.gateway_file")


def normalize_column_names(df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
    """
    Normalize column names to match expected format (case-insensitive, trimmed whitespace).

    Args:
        df: DataFrame with potentially misnamed columns.
        required_columns: List of expected column names.

    Returns:
        DataFrame with normalized column names.
    """
    # Create a mapping from lowercase column names to expected names
    expected_lower = {col.lower().strip(): col for col in required_columns}

    # Build rename mapping
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in expected_lower and col != expected_lower[col_lower]:
            rename_map[col] = expected_lower[col_lower]

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


class GatewayFile:
    """
    Handles loading and processing transaction files for reconciliation.

    Uses a unified template format with columns:
    - Date: Transaction date (YYYY-DD-MM)
    - Reference: Unique transaction identifier
    - Details: Transaction narration/description
    - Debit: Debit amount (outgoing)
    - Credit: Credit amount (incoming)

    Files are loaded using the DataLoader which filters by gateway name prefix.
    """

    def __init__(
        self,
        batch_id: str,
        gateway_name: str,
        data_loader: Optional[DataLoader] = None
    ):
        """
        Initialize GatewayFile.

        Args:
            batch_id: The batch identifier for file storage.
            gateway_name: Gateway name to filter files (e.g., 'equity', 'workpay_equity').
            data_loader: Optional DataLoader instance. Defaults to new DataLoader.
        """
        self.batch_id = batch_id
        self.gateway_name = gateway_name.lower().strip()
        self.data_loader = data_loader or DataLoader()
        self.dataframe: Optional[pd.DataFrame] = None

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Set the dataframe directly (useful for testing)."""
        self.dataframe = df

    def load_data(self) -> None:
        """
        Load data for the gateway from the batch.

        Raises:
            ReadFileException: If no file found or error reading file.
        """
        try:
            df = self.data_loader.load_gateway_data(self.batch_id, self.gateway_name)
            if df.empty:
                raise ReadFileException(
                    f"No data found for gateway '{self.gateway_name}' in batch '{self.batch_id}'"
                )
            self.dataframe = df
        except ReadFileException:
            raise
        except Exception as e:
            raise ReadFileException(
                f"Unexpected error loading data for gateway '{self.gateway_name}': {str(e)}"
            ) from e

    def load_all_data(self) -> None:
        """
        Load data from all files for the gateway and concatenate them.

        Raises:
            ReadFileException: If no files found or error reading files.
        """
        try:
            dataframes = self.data_loader.load_all_gateway_data(self.batch_id, self.gateway_name)
            if not dataframes:
                raise ReadFileException(
                    f"No data found for gateway '{self.gateway_name}' in batch '{self.batch_id}'"
                )
            self.dataframe = pd.concat(dataframes, ignore_index=True)
        except ReadFileException:
            raise
        except Exception as e:
            raise ReadFileException(
                f"Unexpected error loading data for gateway '{self.gateway_name}': {str(e)}"
            ) from e

    def _normalize_column_names(self) -> None:
        """Normalize column names to match expected format (case-insensitive)."""
        if self.dataframe is not None:
            self.dataframe = normalize_column_names(self.dataframe, TEMPLATE_COLUMNS)

    def validate_columns(self) -> None:
        """
        Validate that required template columns are present.

        Raises:
            ColumnValidationException: If dataframe not loaded or columns missing.
        """
        if self.dataframe is None:
            raise ColumnValidationException("DataFrame is not loaded. Call load_data() first.")

        missing_columns: List[str] = [
            col for col in TEMPLATE_COLUMNS if col not in self.dataframe.columns
        ]
        if missing_columns:
            raise ColumnValidationException(
                f"Missing required columns for gateway '{self.gateway_name}': {missing_columns}. "
                f"Found columns: {list(self.dataframe.columns)}"
            )

    def normalize_data(self) -> pd.DataFrame:
        """
        Normalize the loaded data.

        Returns:
            Normalized DataFrame.
        """
        if self.dataframe is None:
            self.load_data()

        # Normalize column names first (case-insensitive matching)
        self._normalize_column_names()
        self.validate_columns()
        self._handle_date_column()
        self._handle_numeric_columns()
        self._handle_string_columns()
        return self.dataframe

    def _handle_date_column(self) -> None:
        """Parse the Date column to datetime (expected format: YYYY-DD-MM)."""
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded.")

        self.dataframe[DATE_COLUMN] = pd.to_datetime(
            self.dataframe[DATE_COLUMN],
            format=TEMPLATE_DATE_FORMAT,
            errors="coerce"
        )

    def _handle_numeric_columns(self) -> None:
        """Convert Debit and Credit columns to numeric."""
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded.")

        for col in [DEBIT_COLUMN, CREDIT_COLUMN]:
            self.dataframe[col] = (
                self.dataframe[col]
                .astype(str)
                .str.strip()
                .str.replace(r"[^\d\.-]", "", regex=True)
            )
            self.dataframe[col] = pd.to_numeric(
                self.dataframe[col], errors="coerce"
            ).fillna(0).abs()

    def _convert_to_clean_string(self, value) -> str:
        """
        Convert a value to a clean string, handling float-to-int conversion.

        Excel often reads numeric Transaction IDs as floats (e.g., 123456 -> 123456.0).
        This method converts them back to clean integers when appropriate.
        """
        if pd.isna(value):
            return ""

        # If it's already a string, just strip it
        if isinstance(value, str):
            return value.strip()

        # If it's a float that represents a whole number, convert to int first
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)

        # For other types (int, etc.), convert directly
        return str(value)

    def _handle_string_columns(self) -> None:
        """Clean string columns, properly handling numeric values."""
        if self.dataframe is None:
            raise ValueError("DataFrame not loaded.")

        string_columns = [REFERENCE_COLUMN, DETAILS_COLUMN]
        null_like_values = {"", "none", "null", "nan", "na"}

        for col in string_columns:
            if col in self.dataframe.columns:
                # Apply clean string conversion (handles float -> int -> str)
                self.dataframe[col] = self.dataframe[col].apply(self._convert_to_clean_string)
                # Replace null-like string values with empty string
                self.dataframe[col] = self.dataframe[col].where(
                    ~self.dataframe[col].str.lower().isin(null_like_values),
                    other=""
                )

    def fill_null_values(self) -> pd.DataFrame:
        """
        Fill null/empty values with defaults for reconciliation.

        Fills:
        - Date: Current date in YYYY-DD-MM format
        - Reference: "NA"
        - Details: "NA"
        - Debit: 0
        - Credit: 0

        Returns:
            DataFrame with nulls filled.
        """
        if self.dataframe is None:
            self.normalize_data()

        # Fill null dates with current date
        current_date = pd.Timestamp(date.today())
        self.dataframe[DATE_COLUMN] = self.dataframe[DATE_COLUMN].fillna(current_date)

        # Fill null Reference and Details with "NA"
        self.dataframe[REFERENCE_COLUMN] = self.dataframe[REFERENCE_COLUMN].replace("", "NA")
        self.dataframe[REFERENCE_COLUMN] = self.dataframe[REFERENCE_COLUMN].fillna("NA")

        self.dataframe[DETAILS_COLUMN] = self.dataframe[DETAILS_COLUMN].replace("", "NA")
        self.dataframe[DETAILS_COLUMN] = self.dataframe[DETAILS_COLUMN].fillna("NA")

        # Fill null Debit and Credit with 0
        self.dataframe[DEBIT_COLUMN] = self.dataframe[DEBIT_COLUMN].fillna(0)
        self.dataframe[CREDIT_COLUMN] = self.dataframe[CREDIT_COLUMN].fillna(0)

        return self.dataframe

    @staticmethod
    def clean_reference_for_key(reference: str) -> str:
        """
        Clean reference value for reconciliation key generation.

        Converts to string, removes decimals, handles edge cases.

        Args:
            reference: The reference value to clean.

        Returns:
            Clean string reference for key generation.
        """
        if pd.isna(reference) or reference in ("", "NA", "na", "N/A"):
            return "NA"

        # Convert to string
        ref_str = str(reference).strip()

        # Handle numeric references that might have decimals
        try:
            ref_float = float(ref_str)
            # Convert to integer (removes decimals) then back to string
            return str(int(ref_float))
        except (ValueError, TypeError):
            # Not a number, return as-is
            return ref_str

    @staticmethod
    def clean_amount_for_key(amount) -> str:
        """
        Clean amount value for reconciliation key generation.

        Converts to absolute whole number (no cents/decimals).

        Args:
            amount: The amount value to clean.

        Returns:
            Clean string amount for key generation.
        """
        if pd.isna(amount):
            return "0"

        try:
            # Convert to absolute value, then to integer (removes decimals)
            amount_float = abs(float(amount))
            return str(int(amount_float))
        except (ValueError, TypeError):
            return "0"

    @staticmethod
    def generate_reconciliation_key(reference: str, amount, base_gateway: str) -> str:
        """
        Generate a reconciliation key for matching transactions.

        Key format: {reference}|{amount}|{base_gateway}

        Args:
            reference: Transaction reference (cleaned to string without decimals).
            amount: Transaction amount (cleaned to absolute whole number).
            base_gateway: Base gateway name (e.g., 'equity').

        Returns:
            Reconciliation key string.
        """
        clean_ref = GatewayFile.clean_reference_for_key(reference)
        clean_amount = GatewayFile.clean_amount_for_key(amount)
        clean_gateway = base_gateway.lower().strip()

        return f"{clean_ref}|{clean_amount}|{clean_gateway}"

    def add_reconciliation_keys(self, base_gateway: str, use_debit: bool = True) -> pd.DataFrame:
        """
        Add reconciliation keys to the dataframe.

        Args:
            base_gateway: Base gateway name for the key (e.g., 'equity').
            use_debit: If True, use Debit column for amount; if False, use Credit.

        Returns:
            DataFrame with 'reconciliation_key' column added.
        """
        if self.dataframe is None:
            self.normalize_data()

        amount_column = DEBIT_COLUMN if use_debit else CREDIT_COLUMN

        self.dataframe['reconciliation_key'] = self.dataframe.apply(
            lambda row: self.generate_reconciliation_key(
                row[REFERENCE_COLUMN],
                row[amount_column] if row[amount_column] > 0 else row[CREDIT_COLUMN if use_debit else DEBIT_COLUMN],
                base_gateway
            ),
            axis=1
        )

        return self.dataframe

    def get_transaction_ids(self) -> set:
        """
        Get unique Reference (Transaction IDs) from the file.

        Returns:
            Set of reference/transaction IDs.
        """
        if self.dataframe is None:
            self.normalize_data()

        return set(
            self.dataframe[REFERENCE_COLUMN]
            .fillna("")
            .astype(str)
            .str.strip()
            .loc[lambda x: x != ""]
        )

    def get_debits(self) -> pd.DataFrame:
        """
        Get all debit transactions (Debit > 0).

        Returns:
            DataFrame with debit transactions.
        """
        try:
            if self.dataframe is None:
                self.normalize_data()

            mask_debit = self.dataframe[DEBIT_COLUMN] > 0
            return self.dataframe.loc[mask_debit].copy()
        except Exception as e:
            raise FileOperationsException("Error extracting debit transactions") from e

    def get_credits(self) -> pd.DataFrame:
        """
        Get all credit transactions (Credit > 0).

        Returns:
            DataFrame with credit transactions.
        """
        try:
            if self.dataframe is None:
                self.normalize_data()

            mask_credit = self.dataframe[CREDIT_COLUMN] > 0
            return self.dataframe.loc[mask_credit].copy()
        except Exception as e:
            raise FileOperationsException("Error extracting credit transactions") from e

    def get_charges(self, charge_keywords: List[str]) -> pd.DataFrame:
        """
        Get charge transactions based on keywords in Reference or Details columns and Debit > 0.

        Transactions are identified as charges if:
        - Debit > 0 AND
        - Reference contains any charge keyword OR Details contains any charge keyword

        Args:
            charge_keywords: Keywords that identify charge transactions.

        Returns:
            DataFrame with charge transactions.
        """
        try:
            if self.dataframe is None:
                self.normalize_data()

            if not charge_keywords:
                return pd.DataFrame(columns=self.dataframe.columns)

            regex_pattern = "|".join(map(re.escape, charge_keywords))

            # Check both Reference and Details columns for charge keywords
            narrative_series = self.dataframe[DETAILS_COLUMN].astype(str)
            reference_series = self.dataframe[REFERENCE_COLUMN].astype(str)

            mask_narrative_keywords = narrative_series.str.contains(regex_pattern, case=False, na=False)
            mask_reference_keywords = reference_series.str.contains(regex_pattern, case=False, na=False)
            mask_keywords = mask_narrative_keywords | mask_reference_keywords
            mask_debits = self.dataframe[DEBIT_COLUMN] > 0

            return self.dataframe.loc[mask_keywords & mask_debits].copy()
        except Exception as e:
            raise FileOperationsException("Error extracting charge transactions") from e

    def get_non_charge_debits(self, charge_keywords: List[str]) -> pd.DataFrame:
        """
        Get debit transactions that are not charges.

        Excludes transactions where:
        - Debit > 0 AND (Reference OR Details contains any charge keyword)

        Args:
            charge_keywords: Keywords that identify charge transactions to exclude.

        Returns:
            DataFrame with non-charge debit transactions.
        """
        try:
            if self.dataframe is None:
                self.normalize_data()

            mask_debits = self.dataframe[DEBIT_COLUMN] > 0

            if not charge_keywords:
                return self.dataframe.loc[mask_debits].copy()

            regex_pattern = "|".join(map(re.escape, charge_keywords))

            # Check both Reference and Details columns for charge keywords
            narrative_series = self.dataframe[DETAILS_COLUMN].astype(str)
            reference_series = self.dataframe[REFERENCE_COLUMN].astype(str)

            mask_narrative_charges = narrative_series.str.contains(regex_pattern, case=False, na=False)
            mask_reference_charges = reference_series.str.contains(regex_pattern, case=False, na=False)
            mask_charges = mask_narrative_charges | mask_reference_charges

            return self.dataframe.loc[mask_debits & ~mask_charges].copy()
        except Exception as e:
            raise FileOperationsException("Error extracting non-charge debit transactions") from e

    def filter_by_narrative(self, keywords: List[str], include: bool = True) -> pd.DataFrame:
        """
        Filter transactions by narrative keywords.

        Args:
            keywords: List of keywords to search for in narrative.
            include: If True, include matching rows. If False, exclude them.

        Returns:
            Filtered DataFrame.
        """
        try:
            if self.dataframe is None:
                self.normalize_data()

            if not keywords:
                return self.dataframe.copy()

            regex_pattern = "|".join(map(re.escape, keywords))
            narrative_series = self.dataframe[DETAILS_COLUMN].astype(str)
            mask = narrative_series.str.contains(regex_pattern, case=False, na=False)

            if include:
                return self.dataframe.loc[mask].copy()
            else:
                return self.dataframe.loc[~mask].copy()
        except Exception as e:
            raise FileOperationsException("Error filtering transactions by narrative") from e

    def get_summary(self) -> dict:
        """
        Get summary statistics for the loaded data.

        Returns:
            Dictionary with summary statistics.
        """
        if self.dataframe is None:
            self.normalize_data()

        total_credits = self.dataframe[CREDIT_COLUMN].sum()
        total_debits = self.dataframe[DEBIT_COLUMN].sum()

        return {
            "gateway": self.gateway_name,
            "batch_id": self.batch_id,
            "total_transactions": len(self.dataframe),
            "total_credits": float(total_credits),
            "total_debits": float(total_debits),
            "net_amount": float(total_credits - total_debits),
            "credit_count": int((self.dataframe[CREDIT_COLUMN] > 0).sum()),
            "debit_count": int((self.dataframe[DEBIT_COLUMN] > 0).sum()),
        }
