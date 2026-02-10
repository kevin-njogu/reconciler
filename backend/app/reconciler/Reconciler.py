"""
Reconciliation Engine.

Reconciles transactions between external (bank) statements and internal records
by matching Reference, Amount, and Gateway using a composite reconciliation key.
"""
import logging
from datetime import datetime
from typing import Optional, List, Tuple

import pandas as pd
import numpy as np
from sqlalchemy import select, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.dataProcessing.GatewayFileClass import GatewayFile
from app.dataLoading.data_loader import DataLoader
from app.sqlModels.transactionEntities import Transaction, TransactionType, ReconciliationCategory
from app.sqlModels.batchEntities import Batch, BatchStatus
from app.pydanticModels.transactionModels import TransactionCreate
from app.upload.template_generator import (
    DATE_COLUMN,
    REFERENCE_COLUMN,
    DETAILS_COLUMN,
    DEBIT_COLUMN,
    CREDIT_COLUMN,
)
from app.storage import get_storage

logger = logging.getLogger("app.reconciler")

# Use the new column names (aliases for backwards compatibility)
TRANSACTION_ID_COLUMN = REFERENCE_COLUMN
NARRATIVE_COLUMN = DETAILS_COLUMN

# Reconciliation columns added to dataframes
RECONCILIATION_STATUS_COLUMN = "Reconciliation Status"
RECONCILIATION_NOTE_COLUMN = "Reconciliation Note"
RECONCILIATION_KEY_COLUMN = "Reconciliation Key"
SOURCE_FILE_COLUMN = "Source File"
BATCH_ID_COLUMN = "Batch Id"
GATEWAY_COLUMN = "gateway"
GATEWAY_TYPE_COLUMN = "gateway_type"
TRANSACTION_TYPE_COLUMN = "transaction_type"
RECONCILIATION_CATEGORY_COLUMN = "reconciliation_category"
IS_MANUAL_COLUMN = "is_manually_reconciled"

# Reconciliation status values
STATUS_RECONCILED = "reconciled"
STATUS_UNRECONCILED = "unreconciled"

# Reconciliation note for system auto-matched transactions
SYSTEM_RECONCILED_NOTE = "System Reconciled"
SYSTEM_RECONCILED_DEPOSIT_NOTE = "System Reconciled - Deposit"
SYSTEM_RECONCILED_CHARGE_NOTE = "System Reconciled - Charge"
SYSTEM_RECONCILED_REFUND_NOTE = "Stored - Refund (Non-reconcilable)"


class FileValidationResult:
    """Result of file validation for a gateway."""

    def __init__(
        self,
        gateway: str,
        has_external: bool = False,
        has_internal: bool = False,
        external_file: Optional[str] = None,
        internal_file: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.gateway = gateway
        self.has_external = has_external
        self.has_internal = has_internal
        self.external_file = external_file
        self.internal_file = internal_file
        self.error = error

    @property
    def is_ready(self) -> bool:
        """Check if both files are available for reconciliation."""
        return self.has_external and self.has_internal

    def to_dict(self) -> dict:
        return {
            "gateway": self.gateway,
            "has_external": self.has_external,
            "has_internal": self.has_internal,
            "external_file": self.external_file,
            "internal_file": self.internal_file,
            "ready_for_reconciliation": self.is_ready,
            "error": self.error,
        }


class ReconciliationSummary:
    """Summary of reconciliation results."""

    def __init__(
        self,
        batch_id: str,
        gateway: str,
        total_external: int = 0,
        total_internal: int = 0,
        matched: int = 0,
        unmatched_external: int = 0,
        unmatched_internal: int = 0,
        deposits_count: int = 0,
        charges_count: int = 0,
    ):
        self.batch_id = batch_id
        self.gateway = gateway
        self.total_external = total_external
        self.total_internal = total_internal
        self.matched = matched
        self.unmatched_external = unmatched_external
        self.unmatched_internal = unmatched_internal
        self.deposits_count = deposits_count
        self.charges_count = charges_count

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "gateway": self.gateway,
            "summary": {
                "total_external": self.total_external,
                "total_internal": self.total_internal,
                "matched": self.matched,
                "unmatched_external": self.unmatched_external,
                "unmatched_internal": self.unmatched_internal,
                "deposits": self.deposits_count,
                "charges": self.charges_count,
            }
        }


class Reconciler:
    """
    Reconciles transactions between external (bank) statements and internal records.

    Matching is done using a composite reconciliation key:
        {reference}|{amount}|{base_gateway}

    Where:
    - reference: Clean string without decimals (e.g., "123456")
    - amount: Absolute whole number (no cents)
    - base_gateway: The gateway name (e.g., "equity")

    Transactions are stored with gateway identifiers:
    - External: {gateway}_external (e.g., "equity_external")
    - Internal: {gateway}_internal (e.g., "equity_internal")
    """

    def __init__(
        self,
        batch_id: str,
        gateway: str,
        db_session: Session,
        charge_keywords: Optional[List[str]] = None,
        data_loader: Optional[DataLoader] = None,
        storage=None
    ):
        """
        Initialize Reconciler.

        Args:
            batch_id: Batch identifier for file storage.
            gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').
            db_session: Database session for saving results.
            charge_keywords: Keywords to identify charge transactions in external file.
            data_loader: Optional DataLoader instance.
            storage: Optional storage backend instance.
        """
        self.batch_id = batch_id
        self.gateway = gateway.lower().strip()
        self.db_session = db_session
        self.charge_keywords = charge_keywords or []
        self.data_loader = data_loader or DataLoader()
        self.storage = storage or get_storage()

        # Gateway identifiers for transactions
        self.external_gateway_id = f"{self.gateway}_external"
        self.internal_gateway_id = f"{self.gateway}_internal"

        # Internal gateway name for file lookup (e.g., "workpay_equity")
        self.internal_gateway_name = f"workpay_{self.gateway}"

        # Source files (populated during validation)
        self.external_file: Optional[str] = None
        self.internal_file: Optional[str] = None

        # DataFrames populated during reconciliation
        self.external_credits: Optional[pd.DataFrame] = None
        self.external_debits: Optional[pd.DataFrame] = None
        self.external_charges: Optional[pd.DataFrame] = None
        self.internal_payouts: Optional[pd.DataFrame] = None

        logger.info(
            f"Reconciler initialized",
            extra={
                "batch_id": batch_id,
                "gateway": self.gateway,
                "external_gateway_id": self.external_gateway_id,
                "internal_gateway_id": self.internal_gateway_id,
                "charge_keywords_count": len(self.charge_keywords),
                "charge_keywords": self.charge_keywords,
            }
        )

    def validate_batch(self) -> Batch:
        """
        Validate that the batch exists and is in pending status.

        Returns:
            Batch object if valid.

        Raises:
            ReconciliationException: If batch not found or not pending.
        """
        stmt = select(Batch).where(Batch.batch_id == self.batch_id)
        batch = self.db_session.execute(stmt).scalar_one_or_none()

        if not batch:
            raise ReconciliationException(f"Batch not found: {self.batch_id}")

        if batch.status != BatchStatus.PENDING.value:
            raise ReconciliationException(
                f"Batch '{self.batch_id}' is not in pending status. "
                f"Current status: {batch.status}"
            )

        return batch

    def validate_files(self) -> FileValidationResult:
        """
        Validate that required files exist for the gateway.

        Checks for:
        - Gateway directory: {batch_id}/{gateway}/
        - External file: {gateway}.xlsx or {gateway}.csv
        - Internal file: workpay_{gateway}.xlsx or workpay_{gateway}.csv

        Returns:
            FileValidationResult with file status.

        Raises:
            ReconciliationException: If gateway directory or files not found.
        """
        result = FileValidationResult(gateway=self.gateway)

        try:
            # List files in the gateway subdirectory
            files = self.storage.list_files(self.batch_id, gateway=self.gateway)

            if not files:
                result.error = (
                    f"No files found for gateway '{self.gateway}' in batch '{self.batch_id}'. "
                    f"Please upload files to proceed with reconciliation."
                )
                raise ReconciliationException(result.error)

            # Look for external file (gateway.xlsx or gateway.csv)
            for filename in files:
                name_lower = filename.lower()
                base_name = name_lower.rsplit('.', 1)[0] if '.' in name_lower else name_lower

                if base_name == self.gateway:
                    result.has_external = True
                    result.external_file = filename
                    self.external_file = filename
                elif base_name == self.internal_gateway_name:
                    result.has_internal = True
                    result.internal_file = filename
                    self.internal_file = filename

            # Validate both files exist
            if not result.has_external:
                result.error = (
                    f"External file not found for gateway '{self.gateway}'. "
                    f"Expected: {self.gateway}.xlsx or {self.gateway}.csv. "
                    f"Found files: {files}"
                )
                raise ReconciliationException(result.error)

            if not result.has_internal:
                result.error = (
                    f"Internal file not found for gateway '{self.gateway}'. "
                    f"Expected: {self.internal_gateway_name}.xlsx or {self.internal_gateway_name}.csv. "
                    f"Found files: {files}"
                )
                raise ReconciliationException(result.error)

            logger.info(
                f"File validation passed",
                extra={
                    "batch_id": self.batch_id,
                    "gateway": self.gateway,
                    "external_file": result.external_file,
                    "internal_file": result.internal_file,
                }
            )

            return result

        except ReconciliationException:
            raise
        except Exception as e:
            result.error = f"Error validating files: {str(e)}"
            raise ReconciliationException(result.error) from e

    def check_existing_reconciliation(self) -> bool:
        """
        Check if reconciliation already exists for this batch and gateway.

        Returns:
            True if transactions already exist, False otherwise.
        """
        stmt = select(Transaction).where(
            and_(
                Transaction.batch_id == self.batch_id,
                or_(
                    Transaction.gateway == self.external_gateway_id,
                    Transaction.gateway == self.internal_gateway_id
                )
            )
        ).limit(1)
        existing = self.db_session.execute(stmt).scalar_one_or_none()
        return existing is not None

    def _load_gateway_file(self, gateway_name: str, source_file: str) -> GatewayFile:
        """
        Load and normalize a gateway file.

        Args:
            gateway_name: Gateway name to load files for.
            source_file: Expected source filename.

        Returns:
            GatewayFile instance with loaded and preprocessed data.
        """
        try:
            gateway_file = GatewayFile(
                batch_id=self.batch_id,
                gateway_name=gateway_name,
                data_loader=self.data_loader
            )
            gateway_file.normalize_data()
            gateway_file.fill_null_values()
            return gateway_file
        except Exception as e:
            raise ReconciliationException(
                f"Failed to load data for gateway '{gateway_name}': {str(e)}"
            ) from e

    def _add_metadata_columns(
        self,
        df: pd.DataFrame,
        gateway_id: str,
        transaction_type: str,
        reconciliation_status: str,
        reconciliation_note: Optional[str] = None,
        source_file: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Add metadata columns to the dataframe.

        Args:
            df: DataFrame to add columns to.
            gateway_id: Full gateway identifier (e.g., "equity_external").
            transaction_type: Transaction type (deposit, debit, charge, payout, etc.).
            reconciliation_status: Initial reconciliation status.
            reconciliation_note: Optional reconciliation note.
            source_file: Source filename.

        Returns:
            DataFrame with metadata columns added including enhanced discriminators.
        """
        df = df.copy()
        df[GATEWAY_COLUMN] = gateway_id
        df[GATEWAY_TYPE_COLUMN] = Transaction.get_gateway_type(gateway_id)
        df[TRANSACTION_TYPE_COLUMN] = transaction_type
        df[RECONCILIATION_CATEGORY_COLUMN] = Transaction.get_reconciliation_category(transaction_type)
        df[RECONCILIATION_STATUS_COLUMN] = reconciliation_status
        df[RECONCILIATION_NOTE_COLUMN] = reconciliation_note
        df[BATCH_ID_COLUMN] = self.batch_id
        df[SOURCE_FILE_COLUMN] = source_file
        df[IS_MANUAL_COLUMN] = None  # Not manually reconciled by default
        return df

    def _generate_reconciliation_key(self, row: pd.Series, use_debit: bool = True) -> str:
        """
        Generate reconciliation key for a transaction row.

        Key format: {reference}|{amount}|{base_gateway}

        Args:
            row: DataFrame row with transaction data.
            use_debit: If True, prefer Debit amount; if False, prefer Credit.

        Returns:
            Reconciliation key string.
        """
        reference = row.get(REFERENCE_COLUMN, "")
        debit = row.get(DEBIT_COLUMN, 0) or 0
        credit = row.get(CREDIT_COLUMN, 0) or 0

        # Determine which amount to use
        if use_debit and debit > 0:
            amount = debit
        elif credit > 0:
            amount = credit
        else:
            amount = debit if debit > 0 else credit

        return GatewayFile.generate_reconciliation_key(reference, amount, self.gateway)

    def _add_reconciliation_keys(
        self,
        df: pd.DataFrame,
        use_debit: bool = True
    ) -> pd.DataFrame:
        """
        Add reconciliation keys to the dataframe.

        Args:
            df: DataFrame to add keys to.
            use_debit: If True, prefer Debit amount for key; if False, prefer Credit.

        Returns:
            DataFrame with reconciliation_key column added.
        """
        df = df.copy()
        df[RECONCILIATION_KEY_COLUMN] = df.apply(
            lambda row: self._generate_reconciliation_key(row, use_debit),
            axis=1
        )
        return df

    def load_dataframes(self) -> None:
        """
        Load all dataframes needed for reconciliation.

        Loads external (bank statement) and internal (workpay) files,
        normalizes them, fills null values, and adds metadata columns.
        """
        logger.info(f"Loading dataframes for batch {self.batch_id}")

        # Load external data
        external_file = self._load_gateway_file(self.gateway, self.external_file)

        # External deposits (credits) - auto-reconciled
        self.external_credits = self._add_metadata_columns(
            external_file.get_credits(),
            self.external_gateway_id,
            TransactionType.DEPOSIT.value,
            STATUS_RECONCILED,
            SYSTEM_RECONCILED_DEPOSIT_NOTE,
            self.external_file
        )
        self.external_credits = self._add_reconciliation_keys(
            self.external_credits, use_debit=False
        )

        # External charges - auto-reconciled
        self.external_charges = self._add_metadata_columns(
            external_file.get_charges(self.charge_keywords),
            self.external_gateway_id,
            TransactionType.CHARGE.value,
            STATUS_RECONCILED,
            SYSTEM_RECONCILED_CHARGE_NOTE,
            self.external_file
        )
        self.external_charges = self._add_reconciliation_keys(
            self.external_charges, use_debit=True
        )

        # External debits - need reconciliation
        self.external_debits = self._add_metadata_columns(
            external_file.get_non_charge_debits(self.charge_keywords),
            self.external_gateway_id,
            TransactionType.DEBIT.value,
            STATUS_UNRECONCILED,
            None,
            self.external_file
        )
        self.external_debits = self._add_reconciliation_keys(
            self.external_debits, use_debit=True
        )

        # Load internal data
        internal_file = self._load_gateway_file(
            self.internal_gateway_name,
            self.internal_file
        )

        # Internal payouts (debits) - need reconciliation against external debits
        self.internal_payouts = self._add_metadata_columns(
            internal_file.get_payouts(),
            self.internal_gateway_id,
            TransactionType.PAYOUT.value,
            STATUS_UNRECONCILED,
            None,
            self.internal_file
        )
        self.internal_payouts = self._add_reconciliation_keys(
            self.internal_payouts, use_debit=True
        )

        logger.info(
            f"Dataframes loaded successfully",
            extra={
                "batch_id": self.batch_id,
                "external_credits": len(self.external_credits) if self.external_credits is not None else 0,
                "external_debits": len(self.external_debits) if self.external_debits is not None else 0,
                "external_charges": len(self.external_charges) if self.external_charges is not None else 0,
                "internal_payouts": len(self.internal_payouts) if self.internal_payouts is not None else 0,
            }
        )

    def _find_duplicates_in_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str
    ) -> List[Tuple[str, int, str]]:
        """
        Find duplicate reconciliation keys within a dataframe.

        Args:
            df: DataFrame to check for duplicates.
            source_name: Human-readable name of the data source.

        Returns:
            List of tuples (reconciliation_key, count, source_name) for duplicates.
        """
        if df is None or df.empty:
            return []

        # Filter out "NA" references as they're placeholders
        valid_df = df[
            (df[REFERENCE_COLUMN] != "NA") &
            (df[REFERENCE_COLUMN] != "") &
            (df[RECONCILIATION_KEY_COLUMN].notna())
        ]

        if valid_df.empty:
            return []

        # Find keys that appear more than once
        key_counts = valid_df[RECONCILIATION_KEY_COLUMN].value_counts()
        duplicates = key_counts[key_counts > 1]

        return [(key, count, source_name) for key, count in duplicates.items()]

    def validate_no_duplicate_keys(self) -> None:
        """
        Validate that there are no duplicate reconciliation keys in the uploaded files.

        This check prevents possible transaction duplication within a batch.
        Duplicate keys within the same file indicate data quality issues.

        Raises:
            ReconciliationException: If duplicate keys are found, with details
                about which keys are duplicated and in which data source.
        """
        if (self.external_credits is None and self.external_debits is None and
            self.external_charges is None and self.internal_payouts is None):
            # Dataframes not loaded yet
            return

        all_duplicates = []

        # Check each dataframe for internal duplicates
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.external_credits, "External Deposits")
        )
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.external_debits, "External Debits")
        )
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.external_charges, "External Charges")
        )
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.internal_payouts, "Internal Payouts")
        )

        if all_duplicates:
            # Format error message with duplicate details
            duplicate_details = []
            for key, count, source in all_duplicates:
                # Parse the key to show meaningful info
                parts = key.split("|")
                if len(parts) >= 2:
                    ref, amount = parts[0], parts[1]
                    duplicate_details.append(
                        f"  - Reference: '{ref}', Amount: {amount}, "
                        f"Occurrences: {count}x in {source}"
                    )
                else:
                    duplicate_details.append(
                        f"  - Key: '{key}', Occurrences: {count}x in {source}"
                    )

            error_message = (
                f"Duplicate transactions detected in batch '{self.batch_id}' "
                f"for gateway '{self.gateway}'. "
                f"Found {len(all_duplicates)} duplicate reconciliation key(s):\n"
                + "\n".join(duplicate_details[:10])  # Limit to first 10
            )

            if len(all_duplicates) > 10:
                error_message += f"\n  ... and {len(all_duplicates) - 10} more duplicates"

            error_message += (
                "\n\nPossible causes:\n"
                "  1. The same transaction appears multiple times in the uploaded file\n"
                "  2. Different transactions have identical Reference and Amount values\n"
                "\nPlease review the uploaded files and remove or correct duplicate entries."
            )

            logger.error(
                f"Duplicate reconciliation keys detected",
                extra={
                    "batch_id": self.batch_id,
                    "gateway": self.gateway,
                    "duplicate_count": len(all_duplicates),
                    "duplicates": all_duplicates[:10],
                }
            )

            raise ReconciliationException(error_message)

    def reconcile(self) -> ReconciliationSummary:
        """
        Perform reconciliation by matching reconciliation keys
        between external debits and internal payouts.

        Key format: {reference}|{amount}|{base_gateway}

        Auto-matched transactions are marked with "System Reconciled" note.

        Returns:
            ReconciliationSummary with reconciliation results.
        """
        if self.external_debits is None or self.internal_payouts is None:
            self.load_dataframes()

        external_df = self.external_debits.copy()
        internal_df = self.internal_payouts.copy()

        # Get reconciliation keys (exclude those with "NA" reference)
        external_keys = set(
            external_df.loc[
                (external_df[REFERENCE_COLUMN] != "NA") &
                (external_df[REFERENCE_COLUMN] != ""),
                RECONCILIATION_KEY_COLUMN
            ]
        )
        internal_keys = set(
            internal_df.loc[
                (internal_df[REFERENCE_COLUMN] != "NA") &
                (internal_df[REFERENCE_COLUMN] != ""),
                RECONCILIATION_KEY_COLUMN
            ]
        )

        # Find matched keys
        matched_keys = external_keys.intersection(internal_keys)

        # Update internal records based on matches
        internal_matched_mask = (
            internal_df[RECONCILIATION_KEY_COLUMN].isin(matched_keys) &
            (internal_df[REFERENCE_COLUMN] != "NA") &
            (internal_df[REFERENCE_COLUMN] != "")
        )
        internal_df.loc[internal_matched_mask, RECONCILIATION_STATUS_COLUMN] = STATUS_RECONCILED
        internal_df.loc[internal_matched_mask, RECONCILIATION_NOTE_COLUMN] = SYSTEM_RECONCILED_NOTE
        internal_df.loc[~internal_matched_mask, RECONCILIATION_STATUS_COLUMN] = STATUS_UNRECONCILED

        # Update external records based on matches
        external_matched_mask = (
            external_df[RECONCILIATION_KEY_COLUMN].isin(matched_keys) &
            (external_df[REFERENCE_COLUMN] != "NA") &
            (external_df[REFERENCE_COLUMN] != "")
        )
        external_df.loc[external_matched_mask, RECONCILIATION_STATUS_COLUMN] = STATUS_RECONCILED
        external_df.loc[external_matched_mask, RECONCILIATION_NOTE_COLUMN] = SYSTEM_RECONCILED_NOTE
        external_df.loc[~external_matched_mask, RECONCILIATION_STATUS_COLUMN] = STATUS_UNRECONCILED

        self.external_debits = external_df
        self.internal_payouts = internal_df

        # Calculate summary
        matched_count = len(external_df[external_df[RECONCILIATION_STATUS_COLUMN] == STATUS_RECONCILED])
        unmatched_external = len(external_df[external_df[RECONCILIATION_STATUS_COLUMN] == STATUS_UNRECONCILED])
        unmatched_internal = len(internal_df[internal_df[RECONCILIATION_STATUS_COLUMN] == STATUS_UNRECONCILED])

        logger.info(
            f"Reconciliation completed",
            extra={
                "batch_id": self.batch_id,
                "gateway": self.gateway,
                "matched": matched_count,
                "unmatched_external": unmatched_external,
                "unmatched_internal": unmatched_internal,
            }
        )

        return ReconciliationSummary(
            batch_id=self.batch_id,
            gateway=self.gateway,
            total_external=len(external_df),
            total_internal=len(internal_df),
            matched=matched_count,
            unmatched_external=unmatched_external,
            unmatched_internal=unmatched_internal,
            deposits_count=len(self.external_credits) if self.external_credits is not None else 0,
            charges_count=len(self.external_charges) if self.external_charges is not None else 0,
        )

    def get_reconciled_external(self) -> pd.DataFrame:
        """Get external debits that were reconciled."""
        if self.external_debits is None:
            self.reconcile()
        return self.external_debits[
            self.external_debits[RECONCILIATION_STATUS_COLUMN] == STATUS_RECONCILED
        ].copy()

    def get_unreconciled_external(self) -> pd.DataFrame:
        """Get external debits that were not reconciled."""
        if self.external_debits is None:
            self.reconcile()
        return self.external_debits[
            self.external_debits[RECONCILIATION_STATUS_COLUMN] == STATUS_UNRECONCILED
        ].copy()

    def get_reconciled_internal(self) -> pd.DataFrame:
        """Get internal payouts that were reconciled."""
        if self.internal_payouts is None:
            self.reconcile()
        return self.internal_payouts[
            self.internal_payouts[RECONCILIATION_STATUS_COLUMN] == STATUS_RECONCILED
        ].copy()

    def get_unreconciled_internal(self) -> pd.DataFrame:
        """Get internal payouts that were not reconciled."""
        if self.internal_payouts is None:
            self.reconcile()
        return self.internal_payouts[
            self.internal_payouts[RECONCILIATION_STATUS_COLUMN] == STATUS_UNRECONCILED
        ].copy()

    def _prepare_dataframe_for_save(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare dataframe for saving to database.

        Selects required columns and handles null conversions for MySQL.

        Args:
            df: DataFrame to prepare.

        Returns:
            Prepared DataFrame ready for database insert.
        """
        columns = [
            GATEWAY_COLUMN,
            GATEWAY_TYPE_COLUMN,
            TRANSACTION_TYPE_COLUMN,
            RECONCILIATION_CATEGORY_COLUMN,
            DATE_COLUMN,
            TRANSACTION_ID_COLUMN,
            NARRATIVE_COLUMN,
            DEBIT_COLUMN,
            CREDIT_COLUMN,
            RECONCILIATION_STATUS_COLUMN,
            RECONCILIATION_NOTE_COLUMN,
            RECONCILIATION_KEY_COLUMN,
            SOURCE_FILE_COLUMN,
            BATCH_ID_COLUMN,
            IS_MANUAL_COLUMN,
        ]
        result = df[[col for col in columns if col in df.columns]].copy()

        # Convert pandas NaT (Not a Time) to None for MySQL compatibility
        if DATE_COLUMN in result.columns:
            result[DATE_COLUMN] = result[DATE_COLUMN].where(
                pd.notnull(result[DATE_COLUMN]), None
            )

        # Handle NaN in numeric columns - convert to None
        for col in [DEBIT_COLUMN, CREDIT_COLUMN]:
            if col in result.columns:
                result[col] = result[col].where(pd.notnull(result[col]), None)

        # Handle NaN in string columns - convert to None
        string_cols = [
            GATEWAY_TYPE_COLUMN,
            RECONCILIATION_CATEGORY_COLUMN,
            RECONCILIATION_NOTE_COLUMN,
            RECONCILIATION_KEY_COLUMN,
            SOURCE_FILE_COLUMN,
            IS_MANUAL_COLUMN,
        ]
        for col in string_cols:
            if col in result.columns:
                result[col] = result[col].where(pd.notnull(result[col]), None)

        return result

    def _save_dataframe(self, df: pd.DataFrame, description: str) -> int:
        """
        Save dataframe to database using pydantic validation.

        Args:
            df: DataFrame to save.
            description: Description for logging.

        Returns:
            Number of records saved.
        """
        if df is None or df.empty:
            return 0

        try:
            prepared_df = self._prepare_dataframe_for_save(df)
            records = prepared_df.to_dict("records")
            validated = [TransactionCreate(**rec) for rec in records]
            payload = [v.model_dump(by_alias=False) for v in validated]

            self.db_session.bulk_insert_mappings(Transaction, payload)
            return len(payload)
        except Exception as e:
            raise DbOperationException(f"Failed to save {description}: {e}")

    def preview(self) -> dict:
        """
        Run reconciliation preview (dry run) without saving to database.

        This allows users to review reconciliation results before committing.
        Results are NOT persisted and will be lost if not saved.

        Steps:
        1. Validate batch exists and is pending
        2. Validate required files exist
        3. Load and process files
        4. Validate no duplicate reconciliation keys
        5. Perform reconciliation
        6. Return results WITHOUT saving

        Returns:
            Dictionary with reconciliation preview results.

        Raises:
            ReconciliationException: If validation fails or duplicate keys detected.
        """
        # Step 1: Validate batch
        self.validate_batch()

        # Step 2: Validate files
        self.validate_files()

        # Step 3: Load data
        self.load_dataframes()

        # Step 4: Validate no duplicate reconciliation keys
        self.validate_no_duplicate_keys()

        # Step 5: Perform reconciliation
        summary = self.reconcile()

        # Calculate match rate
        total_external = summary.total_external
        match_rate = (
            round((summary.matched / total_external) * 100, 1)
            if total_external > 0 else 0.0
        )

        logger.info(
            f"Reconciliation preview completed (dry run)",
            extra={
                "batch_id": self.batch_id,
                "gateway": self.gateway,
                "matched": summary.matched,
                "match_rate": match_rate,
            }
        )

        return {
            "message": "Reconciliation preview completed (not saved)",
            "batch_id": self.batch_id,
            "gateway": self.gateway,
            "is_preview": True,
            **summary.to_dict(),
            "insights": {
                "total_external": summary.total_external,
                "total_internal": summary.total_internal,
                "matched": summary.matched,
                "match_rate": match_rate,
                "unreconciled_external": summary.unmatched_external,
                "unreconciled_internal": summary.unmatched_internal,
                "deposits": summary.deposits_count,
                "charges": summary.charges_count,
            }
        }

    def run(self) -> dict:
        """
        Run the full reconciliation process.

        Steps:
        1. Validate batch exists and is pending
        2. Validate required files exist
        3. Check for existing reconciliation (prevent duplicates)
        4. Load and process files
        5. Validate no duplicate reconciliation keys (prevent transaction duplication)
        6. Perform reconciliation
        7. Save results to database

        Returns:
            Dictionary with reconciliation results.

        Raises:
            ReconciliationException: If validation fails or duplicate keys detected.
            DbOperationException: If database operation fails.
        """
        # Step 1: Validate batch
        self.validate_batch()

        # Step 2: Validate files
        self.validate_files()

        # Step 3: Check for existing reconciliation
        if self.check_existing_reconciliation():
            raise ReconciliationException(
                f"Reconciliation already exists for batch '{self.batch_id}' "
                f"and gateway '{self.gateway}'. "
                "Delete existing records before re-running."
            )

        # Step 4: Load data
        self.load_dataframes()

        # Step 5: Validate no duplicate reconciliation keys
        self.validate_no_duplicate_keys()

        # Step 6: Perform reconciliation
        summary = self.reconcile()

        # Step 7: Save results
        try:
            # Save external records
            deposits_count = self._save_dataframe(
                self.external_credits,
                "external deposits"
            )
            debits_count = self._save_dataframe(
                self.external_debits,
                "external debits"
            )
            charges_count = self._save_dataframe(
                self.external_charges,
                "external charges"
            )

            # Save internal records
            payouts_count = self._save_dataframe(
                self.internal_payouts,
                "internal payouts"
            )

            self.db_session.commit()

            external_total = deposits_count + debits_count + charges_count
            internal_total = payouts_count
            total_saved = external_total + internal_total

            logger.info(
                f"Reconciliation results saved",
                extra={
                    "batch_id": self.batch_id,
                    "gateway": self.gateway,
                    "deposits_saved": deposits_count,
                    "debits_saved": debits_count,
                    "charges_saved": charges_count,
                    "payouts_saved": payouts_count,
                    "total_saved": total_saved,
                }
            )

            return {
                "message": "Reconciliation completed and saved successfully",
                "batch_id": self.batch_id,
                "gateway": self.gateway,
                **summary.to_dict(),
                "saved": {
                    "external_records": external_total,
                    "internal_records": internal_total,
                    "deposits": deposits_count,
                    "debits": debits_count,
                    "charges": charges_count,
                    "payouts": payouts_count,
                    "total": total_saved,
                }
            }

        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(
                f"Duplicate entry during reconciliation save",
                exc_info=True,
                extra={"batch_id": self.batch_id, "error": str(e)}
            )
            raise DbOperationException(f"Duplicate entry detected: {e}")
        except DbOperationException:
            self.db_session.rollback()
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(
                f"Failed to save reconciliation results",
                exc_info=True,
                extra={"batch_id": self.batch_id, "error": str(e)}
            )
            raise DbOperationException(f"Failed to save reconciliation results: {e}")

    # Backwards compatibility method
    def save_results(self) -> dict:
        """
        Save reconciliation results to database.

        This is a backwards-compatible alias for run().

        Returns:
            Dictionary with save counts.
        """
        return self.run()


def get_available_gateways(
    batch_id: str,
    storage=None,
    db_session: Optional[Session] = None
) -> List[dict]:
    """
    Get gateways that have files uploaded for a batch.

    Args:
        batch_id: The batch identifier.
        storage: Optional storage backend.
        db_session: Optional database session for gateway display names.

    Returns:
        List of available gateways with file status.
    """
    from app.config.gateways import get_external_gateways

    storage = storage or get_storage()
    external_gateways = get_external_gateways(db_session)
    available = []

    for gateway in external_gateways:
        result = FileValidationResult(gateway=gateway)

        try:
            files = storage.list_files(batch_id, gateway=gateway)

            for filename in files:
                name_lower = filename.lower()
                base_name = name_lower.rsplit('.', 1)[0] if '.' in name_lower else name_lower

                if base_name == gateway:
                    result.has_external = True
                    result.external_file = filename
                elif base_name == f"workpay_{gateway}":
                    result.has_internal = True
                    result.internal_file = filename

            # Only include gateways that have at least one file
            if result.has_external or result.has_internal:
                # Get display name from config
                from app.config.gateways import get_gateway_config
                config = get_gateway_config(gateway, db_session)
                display_name = config.get("display_name", gateway.title()) if config else gateway.title()

                available.append({
                    **result.to_dict(),
                    "display_name": display_name,
                })

        except Exception as e:
            logger.debug(f"No files found for gateway {gateway}: {e}")
            continue

    return available
