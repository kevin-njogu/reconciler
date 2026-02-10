"""
File Transformation Service.

Transforms raw bank statement and internal record files into the unified template format.
Uses gateway configuration (column_mapping, header_row_config, end_of_data_signal) to
parse raw files and produce normalized CSV output.

Template columns: Date, Reference, Details, Debit, Credit
"""
import logging
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import pandas as pd

from app.upload.template_generator import (
    DATE_COLUMN,
    REFERENCE_COLUMN,
    DETAILS_COLUMN,
    DEBIT_COLUMN,
    CREDIT_COLUMN,
    TEMPLATE_COLUMNS,
)

logger = logging.getLogger("app.file_transformer")

# Default column mapping - maps template columns to common raw column names
DEFAULT_COLUMN_MAPPING: Dict[str, List[str]] = {
    DATE_COLUMN: [
        "date", "transaction date", "trans date", "value date", "posting date",
        "txn date", "trans_date", "transaction_date", "value_date"
    ],
    REFERENCE_COLUMN: [
        "reference", "ref", "ref no", "ref number", "reference number", "ref_no",
        "transaction id", "txn id", "trans id", "transaction_id", "txn_id",
        "receipt", "receipt no", "receipt number", "cheque no", "cheque number"
    ],
    DETAILS_COLUMN: [
        "details", "description", "narrative", "particulars", "remarks",
        "transaction details", "narration", "memo", "transaction description"
    ],
    DEBIT_COLUMN: [
        "debit", "dr", "debit amount", "withdrawal", "withdrawals", "debit_amount",
        "money out", "paid out", "outflow"
    ],
    CREDIT_COLUMN: [
        "credit", "cr", "credit amount", "deposit", "deposits", "credit_amount",
        "money in", "paid in", "inflow"
    ],
}


@dataclass
class TransformationResult:
    """Result of file transformation."""
    success: bool
    normalized_data: Optional[bytes] = None  # CSV bytes
    row_count: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    column_mapping_used: Dict[str, str] = None  # template_col -> raw_col
    unmapped_columns: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.column_mapping_used is None:
            self.column_mapping_used = {}
        if self.unmapped_columns is None:
            self.unmapped_columns = []


class FileTransformer:
    """
    Transforms raw files into the unified template format.

    Uses gateway configuration to:
    - Skip header rows (header_row_config)
    - Map raw columns to template columns (column_mapping)
    - Detect end of data (end_of_data_signal)
    - Parse dates (date_format)
    """

    def __init__(
        self,
        column_mapping: Optional[Dict[str, List[str]]] = None,
        header_row_config: Optional[Dict[str, int]] = None,
        end_of_data_signal: Optional[str] = None,
        date_format: Optional[str] = None,
    ):
        """
        Initialize FileTransformer.

        Args:
            column_mapping: Mapping from template columns to possible raw column names.
                           Falls back to DEFAULT_COLUMN_MAPPING if not provided.
            header_row_config: Rows to skip per file type (e.g., {"xlsx": 5, "csv": 0}).
            end_of_data_signal: Text that signals end of transaction data.
            date_format: Expected date format for parsing (e.g., "YYYY-MM-DD").
        """
        self.column_mapping = column_mapping or DEFAULT_COLUMN_MAPPING
        self.header_row_config = header_row_config or {"xlsx": 0, "xls": 0, "csv": 0}
        self.end_of_data_signal = end_of_data_signal
        self.date_format = date_format

    def transform(self, content: bytes, filename: str) -> TransformationResult:
        """
        Transform a raw file into the normalized template format.

        Args:
            content: Raw file content as bytes.
            filename: Original filename (used to determine file type).

        Returns:
            TransformationResult with normalized CSV data or errors.
        """
        result = TransformationResult(success=False)

        try:
            # Determine file type
            ext = self._get_extension(filename)
            if ext not in [".xlsx", ".xls", ".csv"]:
                result.errors.append(f"Unsupported file type: {ext}")
                return result

            # Get header row skip count
            skip_rows = self._get_skip_rows(ext)

            # Read the file
            df = self._read_file(content, ext, skip_rows)
            if df is None or df.empty:
                result.errors.append("File is empty or could not be read")
                return result

            # Apply end_of_data_signal if configured
            df = self._truncate_at_signal(df)

            # Map columns
            df, mapping_used, unmapped = self._apply_column_mapping(df)
            result.column_mapping_used = mapping_used
            result.unmapped_columns = unmapped

            # Add missing columns with default values instead of failing
            missing = self._get_missing_columns(df)
            if missing:
                df = self._add_missing_columns_with_defaults(df, missing)
                result.warnings.append(
                    f"Unmapped columns filled with defaults: {missing} "
                    f"(Debit/Credit=0, text columns=empty)"
                )

            # Normalize the data
            df = self._normalize_data(df)

            # Convert to CSV
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            result.normalized_data = csv_buffer.getvalue()
            result.row_count = len(df)
            result.success = True

            logger.info(f"Successfully transformed {filename}: {len(df)} rows")

        except Exception as e:
            logger.error(f"Error transforming {filename}: {str(e)}", exc_info=True)
            result.errors.append(f"Transformation error: {str(e)}")

        return result

    def _get_extension(self, filename: str) -> str:
        """Get file extension in lowercase."""
        if "." in filename:
            return "." + filename.lower().rsplit(".", 1)[-1]
        return ""

    def _get_skip_rows(self, ext: str) -> int:
        """Get number of rows to skip for this file type."""
        ext_key = ext.lstrip(".")
        return self.header_row_config.get(ext_key, 0)

    def _read_file(self, content: bytes, ext: str, skip_rows: int) -> Optional[pd.DataFrame]:
        """Read file content into DataFrame."""
        try:
            buffer = BytesIO(content)

            if ext == ".xlsx":
                return pd.read_excel(buffer, engine="openpyxl", skiprows=skip_rows)
            elif ext == ".xls":
                try:
                    return pd.read_excel(buffer, engine="openpyxl", skiprows=skip_rows)
                except Exception:
                    buffer.seek(0)
                    return pd.read_excel(buffer, engine="xlrd", skiprows=skip_rows)
            elif ext == ".csv":
                return pd.read_csv(buffer, skiprows=skip_rows)

        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return None

        return None

    def _truncate_at_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """Truncate DataFrame at end_of_data_signal if configured."""
        if not self.end_of_data_signal:
            return df

        signal = self.end_of_data_signal.lower().strip()

        # Check each row for the signal in any column
        for idx, row in df.iterrows():
            for col in df.columns:
                cell_value = str(row[col]).lower().strip() if pd.notna(row[col]) else ""
                if signal in cell_value:
                    logger.info(f"Found end_of_data_signal at row {idx}")
                    return df.iloc[:idx]

        return df

    def _apply_column_mapping(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
        """
        Apply column mapping to transform raw columns to template columns.

        Returns:
            Tuple of (transformed_df, mapping_used, unmapped_raw_columns)
        """
        mapping_used = {}
        mapped_raw_cols = set()

        # Normalize column names for matching (convert to string first to handle integer column names)
        raw_columns_lower = {str(col).lower().strip(): col for col in df.columns}

        # For each template column, find a matching raw column
        for template_col in TEMPLATE_COLUMNS:
            possible_names = self.column_mapping.get(template_col, [])

            # Ensure possible_names is a list and convert all values to strings
            if not isinstance(possible_names, list):
                possible_names = [possible_names] if possible_names else []

            # Add the template column name itself as a possibility
            # Convert all values to strings before calling .lower() to handle accidental int values
            all_possibilities = [template_col.lower()] + [str(n).lower() for n in possible_names]

            matched = False
            for possible_name in all_possibilities:
                if possible_name in raw_columns_lower:
                    raw_col = raw_columns_lower[possible_name]
                    if raw_col != template_col:
                        df = df.rename(columns={raw_col: template_col})
                    mapping_used[template_col] = raw_col
                    mapped_raw_cols.add(raw_col)
                    matched = True
                    break

            if not matched:
                logger.warning(f"Could not find mapping for template column: {template_col}")

        # Find unmapped raw columns
        unmapped = [col for col in df.columns if col not in mapped_raw_cols and col not in TEMPLATE_COLUMNS]

        return df, mapping_used, unmapped

    def _get_missing_columns(self, df: pd.DataFrame) -> List[str]:
        """Get list of required template columns not in DataFrame."""
        return [col for col in TEMPLATE_COLUMNS if col not in df.columns]

    def _add_missing_columns_with_defaults(
        self, df: pd.DataFrame, missing_columns: List[str]
    ) -> pd.DataFrame:
        """
        Add missing template columns with appropriate default values.

        Numeric columns (Debit, Credit) get 0.
        Text columns (Date, Reference, Details) get empty string.

        Args:
            df: DataFrame to add columns to.
            missing_columns: List of missing column names.

        Returns:
            DataFrame with missing columns added.
        """
        numeric_columns = {DEBIT_COLUMN, CREDIT_COLUMN}

        for col in missing_columns:
            if col in numeric_columns:
                df[col] = 0
                logger.info(f"Added missing column '{col}' with default value 0")
            else:
                df[col] = ""
                logger.info(f"Added missing column '{col}' with default empty string")

        return df

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data types and values."""
        # Keep only template columns
        df = df[TEMPLATE_COLUMNS].copy()

        # Normalize numeric columns
        for col in [DEBIT_COLUMN, CREDIT_COLUMN]:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace(r"[^\d\.-]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).abs()

        # Clean string columns
        for col in [REFERENCE_COLUMN, DETAILS_COLUMN]:
            df[col] = df[col].apply(self._convert_to_clean_string)

        # Handle Date column - keep as-is for now (will be parsed during reconciliation)
        df[DATE_COLUMN] = df[DATE_COLUMN].apply(self._clean_date_value)

        # Remove rows where all transaction values are empty/zero
        mask = (
            (df[DEBIT_COLUMN] > 0) |
            (df[CREDIT_COLUMN] > 0) |
            (df[REFERENCE_COLUMN].str.strip() != "")
        )
        df = df[mask]

        return df.reset_index(drop=True)

    def _convert_to_clean_string(self, value) -> str:
        """Convert value to clean string, handling floats and NaN."""
        if pd.isna(value):
            return ""

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)

        return str(value)

    def _clean_date_value(self, value) -> str:
        """Clean date value for output."""
        if pd.isna(value):
            return ""

        # If it's already a datetime, format it
        if hasattr(value, 'strftime'):
            return value.strftime("%Y-%m-%d")

        # Otherwise return as string
        return str(value).strip()


def create_transformer_from_config(config: dict) -> FileTransformer:
    """
    Create a FileTransformer from gateway file configuration.

    Args:
        config: Gateway file config dict with keys:
                - column_mapping
                - header_row_config
                - end_of_data_signal
                - date_format (optional dict with format_string)

    Returns:
        Configured FileTransformer instance.
    """
    date_format = None
    if config.get("date_format") and isinstance(config["date_format"], dict):
        date_format = config["date_format"].get("format_string")

    return FileTransformer(
        column_mapping=config.get("column_mapping"),
        header_row_config=config.get("header_row_config"),
        end_of_data_signal=config.get("end_of_data_signal"),
        date_format=date_format,
    )
