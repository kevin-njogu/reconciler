"""
Reconciliation Engine.

Reconciles transactions between external (bank) statements and internal records
by matching Reference, Amount, and Gateway using a composite reconciliation key.

Supports carry-forward: previously unreconciled transactions are included in
future reconciliation runs to attempt matching against newly uploaded data.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Tuple, Set

import pandas as pd
import numpy as np
from sqlalchemy import select, and_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.dataProcessing.GatewayFileClass import GatewayFile
from app.dataLoading.data_loader import DataLoader
from app.sqlModels.transactionEntities import Transaction, TransactionType, ReconciliationCategory
from app.sqlModels.runEntities import ReconciliationRun
from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway, FileConfigType
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
RUN_ID_COLUMN = "Run Id"
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


def generate_run_id() -> str:
    """Generate a unique run ID: RUN-YYYYMMDD-HHMMSS-shortid."""
    now = datetime.now()
    short_id = uuid.uuid4().hex[:8]
    return f"RUN-{now.strftime('%Y%m%d-%H%M%S')}-{short_id}"


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
        run_id: str,
        gateway: str,
        total_external: int = 0,
        total_internal: int = 0,
        matched: int = 0,
        unmatched_external: int = 0,
        unmatched_internal: int = 0,
        deposits_count: int = 0,
        charges_count: int = 0,
        carry_forward_matched: int = 0,
        carry_forward_reclassified_charges: int = 0,
    ):
        self.run_id = run_id
        self.gateway = gateway
        self.total_external = total_external
        self.total_internal = total_internal
        self.matched = matched
        self.unmatched_external = unmatched_external
        self.unmatched_internal = unmatched_internal
        self.deposits_count = deposits_count
        self.charges_count = charges_count
        self.carry_forward_matched = carry_forward_matched
        self.carry_forward_reclassified_charges = carry_forward_reclassified_charges

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "gateway": self.gateway,
            "summary": {
                "total_external": self.total_external,
                "total_internal": self.total_internal,
                "matched": self.matched,
                "unmatched_external": self.unmatched_external,
                "unmatched_internal": self.unmatched_internal,
                "deposits": self.deposits_count,
                "charges": self.charges_count,
                "carry_forward_matched": self.carry_forward_matched,
                "carry_forward_reclassified_charges": self.carry_forward_reclassified_charges,
            }
        }


class Reconciler:
    """
    Reconciles transactions between external (bank) statements and internal records.

    Matching is done using a composite reconciliation key:
        {reference}|{amount}|{base_gateway}

    Supports carry-forward: previously unreconciled transactions from the DB
    are included in matching to resolve across reconciliation runs.

    Duplicate transactions are silently skipped via unique constraint on
    (reconciliation_key, gateway).
    """

    def __init__(
        self,
        gateway: str,
        db_session: Session,
        data_loader: Optional[DataLoader] = None,
        storage=None,
        user_id: Optional[int] = None
    ):
        """
        Initialize Reconciler.

        Args:
            gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').
            db_session: Database session for saving results.
            data_loader: Optional DataLoader instance.
            storage: Optional storage backend instance.
            user_id: ID of the user performing reconciliation.
        """
        self.gateway = gateway.lower().strip()
        self.db_session = db_session
        self.data_loader = data_loader or DataLoader()
        self.storage = storage or get_storage()
        self.user_id = user_id
        self.run_id = generate_run_id()

        # Gateway identifiers for transactions
        self.external_gateway_id = f"{self.gateway}_external"
        self.internal_gateway_id = f"{self.gateway}_internal"

        # Internal gateway name for file lookup (e.g., "workpay_equity")
        self.internal_gateway_name = f"workpay_{self.gateway}"

        # Fetch charge keywords from gateway_file_configs DB table
        self.charge_keywords = self._load_charge_keywords()

        # Source files (populated during validation)
        self.external_file: Optional[str] = None
        self.internal_file: Optional[str] = None

        # DataFrames populated during reconciliation
        self.external_credits: Optional[pd.DataFrame] = None
        self.external_debits: Optional[pd.DataFrame] = None
        self.external_charges: Optional[pd.DataFrame] = None
        self.internal_payouts: Optional[pd.DataFrame] = None

        # Carry-forward tracking
        self.carry_forward_external_keys: Set[str] = set()
        self.carry_forward_internal_keys: Set[str] = set()
        self.carry_forward_matched_keys: Set[str] = set()
        self.carry_forward_reclassified_charges: int = 0

        logger.info(
            f"Reconciler initialized",
            extra={
                "run_id": self.run_id,
                "gateway": self.gateway,
                "external_gateway_id": self.external_gateway_id,
                "internal_gateway_id": self.internal_gateway_id,
                "charge_keywords_count": len(self.charge_keywords),
                "charge_keywords": self.charge_keywords,
            }
        )

    def _load_charge_keywords(self) -> List[str]:
        """
        Load charge keywords from the gateway_file_configs table.

        Combines keywords from both external and internal configs for this gateway.
        """
        keywords: List[str] = []
        try:
            stmt = (
                select(GatewayFileConfig.charge_keywords)
                .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
                .where(
                    GatewayFileConfig.name.in_([self.gateway, self.internal_gateway_name]),
                    GatewayFileConfig.is_active == True,
                    Gateway.is_active == True,
                )
            )
            rows = self.db_session.execute(stmt).scalars().all()
            for kw_list in rows:
                if kw_list:
                    keywords.extend(kw_list)

            # Deduplicate while preserving order
            seen = set()
            unique = []
            for kw in keywords:
                kw_lower = kw.lower().strip()
                if kw_lower and kw_lower not in seen:
                    seen.add(kw_lower)
                    unique.append(kw_lower)

            logger.info(
                f"Loaded charge keywords from DB",
                extra={
                    "gateway": self.gateway,
                    "keywords": unique,
                }
            )
            return unique
        except Exception as e:
            logger.warning(f"Failed to load charge keywords from DB: {e}")
            return []

    def validate_files(self) -> FileValidationResult:
        """
        Validate that required files exist for the gateway.

        Checks for:
        - Gateway directory: {gateway}/
        - External file: {gateway}.xlsx or {gateway}.csv
        - Internal file: workpay_{gateway}.xlsx or workpay_{gateway}.csv

        Returns:
            FileValidationResult with file status.

        Raises:
            ReconciliationException: If files not found.
        """
        result = FileValidationResult(gateway=self.gateway)

        try:
            files = self.storage.list_files(self.gateway)

            if not files:
                result.error = (
                    f"No files found for gateway '{self.gateway}'. "
                    f"Please upload files to proceed with reconciliation."
                )
                raise ReconciliationException(result.error)

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
                    "run_id": self.run_id,
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

    def load_carry_forward(self) -> None:
        """
        Load existing unreconciled transactions from the database for carry-forward.

        Queries ALL unreconciled transactions (debits, payouts, and charges) that are
        not pending manual authorization. For external transactions, re-evaluates them
        through the charge keyword engine so previously unreconciled debits that are
        actually charges get reclassified and auto-reconciled.

        Key sets are built for matching:
        - carry_forward_external_keys: unreconciled external debit keys
        - carry_forward_internal_keys: unreconciled internal payout keys
        """
        import re

        try:
            # Load ALL unreconciled transactions for this gateway (not just reconcilable)
            stmt = select(
                Transaction.id,
                Transaction.reconciliation_key,
                Transaction.gateway,
                Transaction.transaction_type,
                Transaction.reconciliation_category,
                Transaction.narrative,
                Transaction.transaction_id,
            ).where(
                and_(
                    Transaction.reconciliation_key.isnot(None),
                    Transaction.reconciliation_status == STATUS_UNRECONCILED,
                    or_(
                        Transaction.gateway == self.external_gateway_id,
                        Transaction.gateway == self.internal_gateway_id
                    ),
                    or_(
                        Transaction.authorization_status.is_(None),
                        Transaction.authorization_status != "pending"
                    ),
                    or_(
                        Transaction.is_manually_reconciled.is_(None),
                        Transaction.is_manually_reconciled != "true"
                    )
                )
            )

            rows = self.db_session.execute(stmt).all()

            reclassified_charge_ids: List[int] = []

            for row in rows:
                txn_id, recon_key, gw, txn_type, recon_cat, narrative, reference = row

                if gw == self.external_gateway_id:
                    # Re-evaluate external transactions through charge keyword engine
                    if self.charge_keywords and txn_type in (
                        TransactionType.DEBIT.value,
                        TransactionType.CHARGE.value,
                    ):
                        is_charge = False
                        if self.charge_keywords:
                            regex_pattern = "|".join(map(re.escape, self.charge_keywords))
                            details_str = str(narrative or "")
                            ref_str = str(reference or "")
                            if (re.search(regex_pattern, details_str, re.IGNORECASE) or
                                    re.search(regex_pattern, ref_str, re.IGNORECASE)):
                                is_charge = True

                        if is_charge and txn_type != TransactionType.CHARGE.value:
                            # Reclassify: was a debit, should be a charge → auto-reconcile
                            reclassified_charge_ids.append(txn_id)
                            # Don't add to carry-forward keys — it's now reconciled
                            continue

                        if is_charge and txn_type == TransactionType.CHARGE.value:
                            # Already a charge but unreconciled — auto-reconcile it
                            reclassified_charge_ids.append(txn_id)
                            continue

                    # Not a charge → add to carry-forward for matching
                    if recon_cat == ReconciliationCategory.RECONCILABLE.value:
                        self.carry_forward_external_keys.add(recon_key)

                elif gw == self.internal_gateway_id:
                    if recon_cat == ReconciliationCategory.RECONCILABLE.value:
                        self.carry_forward_internal_keys.add(recon_key)

            # Batch-update reclassified charges to reconciled
            # NOTE: Do NOT update run_id here — the run record hasn't been created yet
            # (FK to reconciliation_runs.run_id would fail). These transactions keep
            # their original run_id from when they were first saved.
            if reclassified_charge_ids:
                stmt = (
                    update(Transaction)
                    .where(Transaction.id.in_(reclassified_charge_ids))
                    .values(
                        transaction_type=TransactionType.CHARGE.value,
                        reconciliation_category=ReconciliationCategory.AUTO_RECONCILED.value,
                        reconciliation_status=STATUS_RECONCILED,
                        reconciliation_note=f"System Reconciled - Charge (carry-forward reclassified, run: {self.run_id})",
                    )
                )
                self.db_session.execute(stmt)
                self.carry_forward_reclassified_charges = len(reclassified_charge_ids)

            logger.info(
                f"Carry-forward loaded",
                extra={
                    "run_id": self.run_id,
                    "gateway": self.gateway,
                    "carry_forward_external": len(self.carry_forward_external_keys),
                    "carry_forward_internal": len(self.carry_forward_internal_keys),
                    "reclassified_charges": self.carry_forward_reclassified_charges,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to load carry-forward data: {e}", exc_info=True)
            # Non-fatal: reconciliation can proceed without carry-forward

    def _load_gateway_file(self, gateway_name: str, source_file: str) -> GatewayFile:
        """Load and normalize a gateway file."""
        try:
            gateway_file = GatewayFile(
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
        """Add metadata columns to the dataframe."""
        df = df.copy()
        df[GATEWAY_COLUMN] = gateway_id
        df[GATEWAY_TYPE_COLUMN] = Transaction.get_gateway_type(gateway_id)
        df[TRANSACTION_TYPE_COLUMN] = transaction_type
        df[RECONCILIATION_CATEGORY_COLUMN] = Transaction.get_reconciliation_category(transaction_type)
        df[RECONCILIATION_STATUS_COLUMN] = reconciliation_status
        df[RECONCILIATION_NOTE_COLUMN] = reconciliation_note
        df[RUN_ID_COLUMN] = self.run_id
        df[SOURCE_FILE_COLUMN] = source_file
        df[IS_MANUAL_COLUMN] = None
        return df

    def _generate_reconciliation_key(
        self,
        row: pd.Series,
        use_debit: bool = True,
        include_date: bool = False,
    ) -> str:
        """
        Generate reconciliation key for a transaction row.

        For reconcilable transactions (debits/payouts) the key is:
            {reference}|{amount}|{base_gateway}

        For auto-reconciled transactions (charges/deposits) include_date=True
        appends the transaction date so that same-reference, same-amount entries
        on different dates produce distinct keys. This prevents charges and
        deposits from overlapping statement periods being silently skipped as
        cross-run duplicates when they are actually new transactions.
            {reference}|{amount}|{base_gateway}|{YYYYMMDD}
        """
        reference = row.get(REFERENCE_COLUMN, "")
        debit = row.get(DEBIT_COLUMN, 0) or 0
        credit = row.get(CREDIT_COLUMN, 0) or 0

        if use_debit and debit > 0:
            amount = debit
        elif credit > 0:
            amount = credit
        else:
            amount = debit if debit > 0 else credit

        base_key = GatewayFile.generate_reconciliation_key(reference, amount, self.gateway)

        if include_date:
            date_val = row.get(DATE_COLUMN)
            if date_val is not None and not pd.isna(date_val):
                try:
                    date_str = pd.Timestamp(date_val).strftime("%Y%m%d")
                except Exception:
                    date_str = "nodate"
            else:
                date_str = "nodate"
            return f"{base_key}|{date_str}"

        return base_key

    def _add_reconciliation_keys(
        self,
        df: pd.DataFrame,
        use_debit: bool = True,
        include_date: bool = False,
    ) -> pd.DataFrame:
        """Add reconciliation keys to the dataframe."""
        df = df.copy()
        df[RECONCILIATION_KEY_COLUMN] = df.apply(
            lambda row: self._generate_reconciliation_key(row, use_debit, include_date),
            axis=1
        )
        return df

    @staticmethod
    def _deduplicate_keys(df: pd.DataFrame) -> pd.DataFrame:
        """
        Make duplicate reconciliation keys unique by appending a counter suffix.

        Auto-reconciled transactions (charges, deposits) commonly share
        identical references and amounts (e.g., 667 bank charges of KES 15).
        This appends |1, |2, etc. to duplicate keys so each row has a unique
        key for the DB UniqueConstraint on (reconciliation_key, gateway).

        The first occurrence keeps its original key; subsequent duplicates
        get a suffix.
        """
        if df is None or df.empty:
            return df

        df = df.copy()
        key_col = RECONCILIATION_KEY_COLUMN
        seen: dict = {}
        new_keys = []

        for key in df[key_col]:
            if key in seen:
                seen[key] += 1
                new_keys.append(f"{key}|{seen[key]}")
            else:
                seen[key] = 0
                new_keys.append(key)

        df[key_col] = new_keys
        return df

    def load_dataframes(self) -> None:
        """
        Load all dataframes needed for reconciliation.

        Loads external (bank statement) and internal (workpay) files,
        normalizes them, fills null values, and adds metadata columns.
        """
        logger.info(f"Loading dataframes for run {self.run_id}")

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
            self.external_credits, use_debit=False, include_date=True
        )
        self.external_credits = self._deduplicate_keys(self.external_credits)

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
            self.external_charges, use_debit=True, include_date=True
        )
        self.external_charges = self._deduplicate_keys(self.external_charges)

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
                "run_id": self.run_id,
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
        """Find duplicate reconciliation keys within a dataframe."""
        if df is None or df.empty:
            return []

        valid_df = df[
            (df[REFERENCE_COLUMN] != "NA") &
            (df[REFERENCE_COLUMN] != "") &
            (df[RECONCILIATION_KEY_COLUMN].notna())
        ]

        if valid_df.empty:
            return []

        key_counts = valid_df[RECONCILIATION_KEY_COLUMN].value_counts()
        duplicates = key_counts[key_counts > 1]

        return [(key, count, source_name) for key, count in duplicates.items()]

    def validate_no_duplicate_keys(self) -> None:
        """
        Validate that there are no duplicate reconciliation keys in the uploaded files.

        Only checks reconcilable transactions (external debits and internal payouts).
        Auto-reconciled transactions (deposits, charges) are excluded because they
        commonly have identical references and amounts (e.g., bank charges of the
        same fee). Their keys are deduplicated before saving.

        Raises:
            ReconciliationException: If duplicate keys are found.
        """
        if self.external_debits is None and self.internal_payouts is None:
            return

        all_duplicates = []
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.external_debits, "External Debits")
        )
        all_duplicates.extend(
            self._find_duplicates_in_dataframe(self.internal_payouts, "Internal Payouts")
        )

        if all_duplicates:
            duplicate_details = []
            for key, count, source in all_duplicates:
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
                f"Duplicate transactions detected for gateway '{self.gateway}'. "
                f"Found {len(all_duplicates)} duplicate reconciliation key(s):\n"
                + "\n".join(duplicate_details[:10])
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
                    "run_id": self.run_id,
                    "gateway": self.gateway,
                    "duplicate_count": len(all_duplicates),
                }
            )

            raise ReconciliationException(error_message)

    def reconcile(self) -> ReconciliationSummary:
        """
        Perform reconciliation by matching reconciliation keys
        between external debits and internal payouts.

        Includes carry-forward keys from previously unreconciled DB transactions.

        Returns:
            ReconciliationSummary with reconciliation results.
        """
        if self.external_debits is None or self.internal_payouts is None:
            self.load_dataframes()

        external_df = self.external_debits.copy()
        internal_df = self.internal_payouts.copy()

        # Get reconciliation keys from new file data (exclude "NA" references)
        new_external_keys = set(
            external_df.loc[
                (external_df[REFERENCE_COLUMN] != "NA") &
                (external_df[REFERENCE_COLUMN] != ""),
                RECONCILIATION_KEY_COLUMN
            ]
        )
        new_internal_keys = set(
            internal_df.loc[
                (internal_df[REFERENCE_COLUMN] != "NA") &
                (internal_df[REFERENCE_COLUMN] != ""),
                RECONCILIATION_KEY_COLUMN
            ]
        )

        # Combine with carry-forward keys for matching
        all_external_keys = new_external_keys | self.carry_forward_external_keys
        all_internal_keys = new_internal_keys | self.carry_forward_internal_keys

        # Find matched keys (new + carry-forward combined)
        matched_keys = all_external_keys.intersection(all_internal_keys)

        # Track which carry-forward keys got matched in this run
        self.carry_forward_matched_keys = set()
        for key in matched_keys:
            if key in self.carry_forward_external_keys or key in self.carry_forward_internal_keys:
                self.carry_forward_matched_keys.add(key)

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
                "run_id": self.run_id,
                "gateway": self.gateway,
                "matched": matched_count,
                "unmatched_external": unmatched_external,
                "unmatched_internal": unmatched_internal,
                "carry_forward_matched": len(self.carry_forward_matched_keys),
            }
        )

        return ReconciliationSummary(
            run_id=self.run_id,
            gateway=self.gateway,
            total_external=len(external_df),
            total_internal=len(internal_df),
            matched=matched_count,
            unmatched_external=unmatched_external,
            unmatched_internal=unmatched_internal,
            deposits_count=len(self.external_credits) if self.external_credits is not None else 0,
            charges_count=len(self.external_charges) if self.external_charges is not None else 0,
            carry_forward_matched=len(self.carry_forward_matched_keys),
            carry_forward_reclassified_charges=self.carry_forward_reclassified_charges,
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
        """Prepare dataframe for saving to database."""
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
            RUN_ID_COLUMN,
            IS_MANUAL_COLUMN,
        ]
        result = df[[col for col in columns if col in df.columns]].copy()

        # Convert pandas NaT to None for MySQL compatibility
        if DATE_COLUMN in result.columns:
            result[DATE_COLUMN] = result[DATE_COLUMN].where(
                pd.notnull(result[DATE_COLUMN]), None
            )

        # Handle NaN in numeric columns
        for col in [DEBIT_COLUMN, CREDIT_COLUMN]:
            if col in result.columns:
                result[col] = result[col].where(pd.notnull(result[col]), None)

        # Handle NaN in string columns
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

    def _save_dataframe(self, df: pd.DataFrame, description: str) -> Tuple[int, int]:
        """
        Save dataframe to database, skipping duplicates silently.

        Args:
            df: DataFrame to save.
            description: Description for logging.

        Returns:
            Tuple of (records_saved, records_skipped).
        """
        if df is None or df.empty:
            return 0, 0

        try:
            prepared_df = self._prepare_dataframe_for_save(df)
            records = prepared_df.to_dict("records")
            validated = [TransactionCreate(**rec) for rec in records]
            payload = [v.model_dump(by_alias=False) for v in validated]

            saved = 0
            skipped = 0
            for record in payload:
                try:
                    # Use SAVEPOINT so a duplicate only rolls back this row, not the whole transaction
                    nested = self.db_session.begin_nested()
                    self.db_session.execute(
                        Transaction.__table__.insert().values(**record)
                    )
                    nested.commit()
                    saved += 1
                except IntegrityError:
                    nested.rollback()
                    skipped += 1
                    logger.debug(
                        f"Skipped duplicate: {record.get('reconciliation_key')} "
                        f"in {record.get('gateway')}"
                    )

            if skipped > 0:
                logger.info(
                    f"Duplicates skipped during save",
                    extra={
                        "description": description,
                        "saved": saved,
                        "skipped": skipped,
                    }
                )

            return saved, skipped
        except IntegrityError:
            raise
        except Exception as e:
            raise DbOperationException(f"Failed to save {description}: {e}")

    def _update_carry_forward_matches(self) -> int:
        """
        Update existing unreconciled DB transactions that matched in this run.

        Sets their status to reconciled and assigns the current run_id.

        Returns:
            Number of carry-forward transactions updated.
        """
        if not self.carry_forward_matched_keys:
            return 0

        try:
            stmt = (
                update(Transaction)
                .where(
                    and_(
                        Transaction.reconciliation_key.in_(self.carry_forward_matched_keys),
                        Transaction.reconciliation_status == STATUS_UNRECONCILED,
                        or_(
                            Transaction.gateway == self.external_gateway_id,
                            Transaction.gateway == self.internal_gateway_id
                        )
                    )
                )
                .values(
                    reconciliation_status=STATUS_RECONCILED,
                    reconciliation_note=f"System Reconciled (carry-forward, run: {self.run_id})",
                    run_id=self.run_id,
                )
            )
            result = self.db_session.execute(stmt)
            updated = result.rowcount

            logger.info(
                f"Carry-forward matches updated",
                extra={
                    "run_id": self.run_id,
                    "gateway": self.gateway,
                    "updated": updated,
                }
            )
            return updated
        except Exception as e:
            logger.error(f"Failed to update carry-forward matches: {e}")
            raise DbOperationException(f"Failed to update carry-forward matches: {e}")

    def _create_run_record(self, summary: ReconciliationSummary) -> None:
        """Create a ReconciliationRun record in the database."""
        run = ReconciliationRun(
            run_id=self.run_id,
            gateway=self.gateway,
            status="completed",
            total_external=summary.total_external,
            total_internal=summary.total_internal,
            matched=summary.matched,
            unmatched_external=summary.unmatched_external,
            unmatched_internal=summary.unmatched_internal,
            carry_forward_matched=summary.carry_forward_matched,
            created_by_id=self.user_id,
        )
        self.db_session.add(run)

    def preview(self) -> dict:
        """
        Run reconciliation preview (dry run) without saving to database.

        Steps:
        1. Validate required files exist
        2. Load carry-forward data
        3. Load and process files
        4. Validate no duplicate reconciliation keys
        5. Perform reconciliation (with carry-forward matching)
        6. Return results WITHOUT saving

        Returns:
            Dictionary with reconciliation preview results.
        """
        # Step 1: Validate files
        self.validate_files()

        # Step 2: Load carry-forward data
        self.load_carry_forward()

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
                "run_id": self.run_id,
                "gateway": self.gateway,
                "matched": summary.matched,
                "match_rate": match_rate,
                "carry_forward_matched": summary.carry_forward_matched,
            }
        )

        return {
            "message": "Reconciliation preview completed (not saved)",
            "run_id": self.run_id,
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
                "carry_forward_matched": summary.carry_forward_matched,
                "carry_forward_reclassified_charges": summary.carry_forward_reclassified_charges,
                "carry_forward_external_pool": len(self.carry_forward_external_keys),
                "carry_forward_internal_pool": len(self.carry_forward_internal_keys),
            }
        }

    def run(self) -> dict:
        """
        Run the full reconciliation process.

        Steps:
        1. Validate required files exist
        2. Load carry-forward data
        3. Load and process files
        4. Validate no duplicate reconciliation keys
        5. Perform reconciliation (with carry-forward)
        6. Save new transactions (skip duplicates)
        7. Update carry-forward matches in DB
        8. Create reconciliation run record

        Returns:
            Dictionary with reconciliation results.
        """
        # Step 1: Validate files
        self.validate_files()

        # Step 2: Load carry-forward data
        self.load_carry_forward()

        # Step 3: Load data
        self.load_dataframes()

        # Step 4: Validate no duplicate reconciliation keys
        self.validate_no_duplicate_keys()

        # Step 5: Perform reconciliation
        summary = self.reconcile()

        # Step 6-8: Save results
        try:
            # Create run record FIRST — transactions have FK to reconciliation_runs.run_id
            self._create_run_record(summary)
            self.db_session.flush()

            # Save external records (skip duplicates)
            deposits_saved, deposits_skipped = self._save_dataframe(
                self.external_credits, "external deposits"
            )
            debits_saved, debits_skipped = self._save_dataframe(
                self.external_debits, "external debits"
            )
            charges_saved, charges_skipped = self._save_dataframe(
                self.external_charges, "external charges"
            )

            # Save internal records (skip duplicates)
            payouts_saved, payouts_skipped = self._save_dataframe(
                self.internal_payouts, "internal payouts"
            )

            # Update carry-forward matches
            carry_forward_updated = self._update_carry_forward_matches()

            self.db_session.commit()

            external_total = deposits_saved + debits_saved + charges_saved
            internal_total = payouts_saved
            total_saved = external_total + internal_total
            total_skipped = deposits_skipped + debits_skipped + charges_skipped + payouts_skipped

            logger.info(
                f"Reconciliation results saved",
                extra={
                    "run_id": self.run_id,
                    "gateway": self.gateway,
                    "total_saved": total_saved,
                    "total_skipped": total_skipped,
                    "carry_forward_updated": carry_forward_updated,
                }
            )

            return {
                "message": "Reconciliation completed and saved successfully",
                "run_id": self.run_id,
                "gateway": self.gateway,
                **summary.to_dict(),
                "saved": {
                    "external_records": external_total,
                    "internal_records": internal_total,
                    "deposits": deposits_saved,
                    "debits": debits_saved,
                    "charges": charges_saved,
                    "payouts": payouts_saved,
                    "total": total_saved,
                    "duplicates_skipped": total_skipped,
                    "carry_forward_updated": carry_forward_updated,
                    "carry_forward_reclassified_charges": self.carry_forward_reclassified_charges,
                }
            }

        except DbOperationException:
            self.db_session.rollback()
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(
                f"Failed to save reconciliation results",
                exc_info=True,
                extra={"run_id": self.run_id, "error": str(e)}
            )
            raise DbOperationException(f"Failed to save reconciliation results: {e}")


def get_available_gateways(
    storage=None,
    db_session: Optional[Session] = None
) -> List[dict]:
    """
    Get gateways that have files uploaded and ready for reconciliation.

    Scans storage directories for each configured gateway to check file availability.

    Args:
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
            files = storage.list_files(gateway)

            for filename in files:
                name_lower = filename.lower()
                base_name = name_lower.rsplit('.', 1)[0] if '.' in name_lower else name_lower

                if base_name == gateway:
                    result.has_external = True
                    result.external_file = filename
                elif base_name == f"workpay_{gateway}":
                    result.has_internal = True
                    result.internal_file = filename

            if result.has_external or result.has_internal:
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
