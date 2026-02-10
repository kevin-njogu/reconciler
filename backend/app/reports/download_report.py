"""
Report generation for reconciliation results.

Generates Excel and CSV reports from the unified transactions table.

Report Columns (as per requirements):
- Date: Transaction date
- Transaction Reference: Unique transaction identifier
- Details: Transaction narration/description
- Debit: Debit amount
- Credit: Credit amount
- Reconciliation Status: reconciled/unreconciled
- Reconciliation Note: Manual or system reconciliation note
- Reconciliation Key: Composite key used for matching
- Batch ID: Batch identifier

Excel Format Sheets:
- {Gateway} External Debits: External debit transactions
- Workpay {Gateway} Debits: Internal/workpay debit transactions
- {Gateway} Credits Deposits: External credit/deposit transactions
- {Gateway} Charges: Bank charges
"""
import csv
from io import BytesIO, StringIO
from typing import Optional, List, Dict, Literal

import pandas as pd
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.reports.output_writer import write_to_excel
from app.sqlModels.transactionEntities import Transaction, TransactionType, Gateway
from app.pydanticModels.transactionModels import TransactionResponse
from app.config.gateways import get_internal_gateways


# Report format types
ReportFormat = Literal["xlsx", "csv"]


def load_transactions(
    db_session: Session,
    batch_id: str,
    gateway: Optional[str] = None,
    transaction_type: Optional[str] = None,
    reconciliation_status: Optional[str] = None
) -> List[Transaction]:
    """
    Load transactions from database with optional filters.

    Args:
        db_session: Database session.
        batch_id: Batch ID to filter by.
        gateway: Optional gateway filter (equity, kcb, mpesa, workpay).
        transaction_type: Optional transaction type filter (credit, debit, charge, payout).
        reconciliation_status: Optional status filter (reconciled, unreconciled).

    Returns:
        List of Transaction records.
    """
    conditions = [Transaction.batch_id == batch_id]

    if gateway:
        conditions.append(Transaction.gateway == gateway.lower())
    if transaction_type:
        conditions.append(Transaction.transaction_type == transaction_type.lower())
    if reconciliation_status:
        conditions.append(Transaction.reconciliation_status == reconciliation_status.lower())

    stmt = select(Transaction).where(and_(*conditions))
    return db_session.execute(stmt).scalars().all()


def load_transactions_for_gateway(
    db_session: Session,
    batch_id: str,
    base_gateway: str
) -> List[Transaction]:
    """
    Load all transactions for a base gateway (both external and internal).

    For example, if base_gateway is 'equity', this loads:
    - equity_external transactions
    - equity_internal transactions (or workpay_equity)

    Args:
        db_session: Database session.
        batch_id: Batch ID to filter by.
        base_gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').

    Returns:
        List of Transaction records for both external and internal.
    """
    base_lower = base_gateway.lower()

    # Match gateways that are the base gateway itself or end with the base gateway
    # e.g., 'equity', 'equity_external', 'equity_internal', 'workpay_equity'
    stmt = select(Transaction).where(
        and_(
            Transaction.batch_id == batch_id,
            or_(
                Transaction.gateway == base_lower,
                Transaction.gateway == f"{base_lower}_external",
                Transaction.gateway == f"{base_lower}_internal",
                Transaction.gateway.endswith(f"_{base_lower}")
            )
        )
    ).order_by(Transaction.date, Transaction.id)

    return db_session.execute(stmt).scalars().all()


def transactions_to_report_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """
    Convert transaction records to report DataFrame with required columns.

    Columns: Date, Transaction Reference, Details, Debit, Credit,
             Reconciliation Status, Reconciliation Note, Reconciliation Key, Batch ID

    Args:
        transactions: List of Transaction records.

    Returns:
        DataFrame with transaction data in report format.
    """
    if not transactions:
        return pd.DataFrame(columns=[
            "Date", "Transaction Reference", "Details", "Debit", "Credit",
            "Reconciliation Status", "Reconciliation Note", "Reconciliation Key", "Batch ID"
        ])

    records = []
    for t in transactions:
        # Determine the reconciliation note to display
        # Priority: manual_recon_note > reconciliation_note (for system reconciled)
        recon_note = ""
        if t.manual_recon_note:
            recon_note = t.manual_recon_note
        elif t.reconciliation_note:
            recon_note = t.reconciliation_note

        records.append({
            "Date": t.date.strftime("%Y-%m-%d") if t.date else "",
            "Transaction Reference": t.transaction_id or "",
            "Details": t.narrative or "",
            "Debit": float(t.debit) if t.debit else 0.0,
            "Credit": float(t.credit) if t.credit else 0.0,
            "Reconciliation Status": t.reconciliation_status or "",
            "Reconciliation Note": recon_note,
            "Reconciliation Key": t.reconciliation_key or "",
            "Batch ID": t.batch_id or "",
        })

    return pd.DataFrame(records)


def transactions_to_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """
    Convert transaction records to DataFrame (legacy format for summary reports).

    Uses the unified template format: Date, Reference, Details, Debit, Credit

    Args:
        transactions: List of Transaction records.

    Returns:
        DataFrame with transaction data.
    """
    if not transactions:
        return pd.DataFrame()

    records = []
    for t in transactions:
        # Determine the reconciliation note to display
        # Priority: manual_recon_note > reconciliation_note (for system reconciled)
        recon_note = None
        if t.manual_recon_note:
            recon_note = t.manual_recon_note
        elif t.reconciliation_note:
            recon_note = t.reconciliation_note

        records.append({
            "Date": t.date,
            "Reference": t.transaction_id,
            "Details": t.narrative,
            "Gateway": t.gateway,
            "Type": t.transaction_type,
            "Debit": float(t.debit) if t.debit else None,
            "Credit": float(t.credit) if t.credit else None,
            "Reconciliation Status": t.reconciliation_status,
            "Reconciliation Note": recon_note,
            "Batch ID": t.batch_id,
        })

    return pd.DataFrame(records)


def derive_internal_gateway(db_session: Session, external_gateway: str) -> str:
    """
    Derive the internal gateway name for an external gateway from the database.

    Args:
        db_session: Database session.
        external_gateway: External gateway name (e.g., 'equity', 'mpesa').

    Returns:
        Internal gateway name (e.g., 'workpay_equity', 'workpay_mpesa').

    Raises:
        ValueError: If no matching internal gateway found.
    """
    external_lower = external_gateway.lower()
    internal_gateways = get_internal_gateways(db_session)

    # Find internal gateway that ends with _{external_gateway}
    matching = [gw for gw in internal_gateways if gw.endswith(f"_{external_lower}")]
    if not matching:
        raise ValueError(
            f"No internal gateway found for external gateway '{external_gateway}'. "
            f"Available internal gateways: {internal_gateways}"
        )
    return matching[0]


def generate_gateway_report(
    db_session: Session,
    batch_id: str,
    gateway: str
) -> Dict[str, pd.DataFrame]:
    """
    Generate report DataFrames for a specific gateway.

    Args:
        db_session: Database session.
        batch_id: Batch ID to report on.
        gateway: Gateway name (equity, kcb, mpesa).

    Returns:
        Dictionary of sheet name to DataFrame.
    """
    gateway_lower = gateway.lower()
    # Derive internal gateway from database
    internal_gateway = derive_internal_gateway(db_session, gateway_lower)

    # Load external transactions (credits, debits, charges)
    credits = load_transactions(
        db_session, batch_id,
        gateway=gateway_lower,
        transaction_type=TransactionType.DEPOSIT.value
    )
    debits = load_transactions(
        db_session, batch_id,
        gateway=gateway_lower,
        transaction_type=TransactionType.DEBIT.value
    )
    charges = load_transactions(
        db_session, batch_id,
        gateway=gateway_lower,
        transaction_type=TransactionType.CHARGE.value
    )

    # Load internal transactions (workpay_{gateway})
    internal_payouts = load_transactions(
        db_session, batch_id,
        gateway=internal_gateway,
        transaction_type=TransactionType.PAYOUT.value
    )

    # Build DataFrames
    dataframes = {
        f"{gateway}_credits": transactions_to_dataframe(credits),
        f"{gateway}_debits": transactions_to_dataframe(debits),
        f"{gateway}_charges": transactions_to_dataframe(charges),
        f"{internal_gateway}_payouts": transactions_to_dataframe(internal_payouts),
    }

    # Filter out empty DataFrames
    return {name: df for name, df in dataframes.items() if not df.empty}


def generate_reconciliation_summary(
    db_session: Session,
    batch_id: str,
    gateway: str
) -> pd.DataFrame:
    """
    Generate a comprehensive summary of reconciliation results.

    Includes:
    - Transaction counts (total, reconciled, unreconciled)
    - Amount totals broken down by reconciliation status
    - Separate sections for external and internal records

    Args:
        db_session: Database session.
        batch_id: Batch ID to summarize.
        gateway: Gateway name.

    Returns:
        DataFrame with detailed summary statistics.
    """
    gateway_lower = gateway.lower()
    # Derive internal gateway from database
    internal_gateway = derive_internal_gateway(db_session, gateway_lower)

    # Load all transactions
    all_external = load_transactions(db_session, batch_id, gateway=gateway_lower)
    all_internal = load_transactions(db_session, batch_id, gateway=internal_gateway)

    # Filter external by type
    external_debits = [t for t in all_external if t.transaction_type == TransactionType.DEBIT.value]
    external_credits = [t for t in all_external if t.transaction_type == TransactionType.DEPOSIT.value]
    external_charges = [t for t in all_external if t.transaction_type == TransactionType.CHARGE.value]

    # External debit counts
    external_debits_reconciled = [t for t in external_debits if t.reconciliation_status == "reconciled"]
    external_debits_unreconciled = [t for t in external_debits if t.reconciliation_status == "unreconciled"]

    # External debit amounts
    external_debits_reconciled_total = sum(float(t.debit or 0) for t in external_debits_reconciled)
    external_debits_unreconciled_total = sum(float(t.debit or 0) for t in external_debits_unreconciled)
    external_debits_total = external_debits_reconciled_total + external_debits_unreconciled_total

    # External credits total
    external_credits_total = sum(float(t.credit or 0) for t in external_credits)

    # External charges total
    external_charges_total = sum(float(t.debit or 0) for t in external_charges)

    # Internal counts
    internal_reconciled = [t for t in all_internal if t.reconciliation_status == "reconciled"]
    internal_unreconciled = [t for t in all_internal if t.reconciliation_status == "unreconciled"]

    # Internal amounts (using debit and credit columns from unified format)
    def get_amount(t):
        """Get transaction amount from debit or credit column."""
        return float(t.debit or 0) + float(t.credit or 0)

    internal_reconciled_total = sum(get_amount(t) for t in internal_reconciled)
    internal_unreconciled_total = sum(get_amount(t) for t in internal_unreconciled)
    internal_total = internal_reconciled_total + internal_unreconciled_total

    summary_data = {
        "Category": [
            # Header info
            "BATCH INFORMATION",
            "External Gateway",
            "Internal Gateway",
            "Batch ID",
            "",
            # External Summary
            "EXTERNAL RECORDS (BANK STATEMENT)",
            "Total Debits Count",
            "Reconciled Debits Count",
            "Unreconciled Debits Count",
            "Total Credits Count",
            "Total Charges Count",
            "",
            "EXTERNAL AMOUNTS",
            "Total Debits Amount",
            "Reconciled Debits Amount",
            "Unreconciled Debits Amount",
            "Total Credits Amount",
            "Total Charges Amount",
            "",
            # Internal Summary
            "INTERNAL RECORDS (WORKPAY)",
            "Total Transactions Count",
            "Reconciled Count",
            "Unreconciled Count",
            "",
            "INTERNAL AMOUNTS",
            "Total Amount",
            "Reconciled Amount",
            "Unreconciled Amount",
            "",
            # Variance
            "RECONCILIATION VARIANCE",
            "External Debits vs Internal (Count)",
            "External Debits vs Internal (Amount)",
        ],
        "Value": [
            # Header info
            "",
            gateway.upper(),
            internal_gateway.upper(),
            batch_id,
            "",
            # External Summary
            "",
            len(external_debits),
            len(external_debits_reconciled),
            len(external_debits_unreconciled),
            len(external_credits),
            len(external_charges),
            "",
            "",
            f"{external_debits_total:,.2f}",
            f"{external_debits_reconciled_total:,.2f}",
            f"{external_debits_unreconciled_total:,.2f}",
            f"{external_credits_total:,.2f}",
            f"{external_charges_total:,.2f}",
            "",
            # Internal Summary
            "",
            len(all_internal),
            len(internal_reconciled),
            len(internal_unreconciled),
            "",
            "",
            f"{internal_total:,.2f}",
            f"{internal_reconciled_total:,.2f}",
            f"{internal_unreconciled_total:,.2f}",
            "",
            # Variance
            "",
            len(external_debits) - len(all_internal),
            f"{external_debits_total - internal_total:,.2f}",
        ]
    }

    return pd.DataFrame(summary_data)


def download_gateway_report(
    db_session: Session,
    gateway: str,
    batch_id: str
) -> StreamingResponse:
    """
    Generate and download reconciliation report for a gateway.

    Args:
        db_session: Database session.
        gateway: Gateway name (equity, kcb, mpesa).
        batch_id: Batch ID to report on.

    Returns:
        StreamingResponse with Excel file.

    Raises:
        Exception: If report generation fails.
    """
    try:
        # Generate report DataFrames
        dataframes = generate_gateway_report(db_session, batch_id, gateway)

        # Add summary sheet
        summary = generate_reconciliation_summary(db_session, batch_id, gateway)
        dataframes = {"Summary": summary, **dataframes}

        # Write to Excel
        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        # Generate filename
        filename = f"{gateway.capitalize()}_{batch_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception:
        raise


def download_full_report(
    db_session: Session,
    batch_id: str
) -> StreamingResponse:
    """
    Generate and download full reconciliation report for all gateways.

    Args:
        db_session: Database session.
        batch_id: Batch ID to report on.

    Returns:
        StreamingResponse with Excel file.
    """
    try:
        # Load all transactions for the batch
        all_transactions = load_transactions(db_session, batch_id)

        if not all_transactions:
            # Return empty report
            output = BytesIO()
            pd.DataFrame({"Message": ["No transactions found for this batch"]}).to_excel(
                output, index=False, engine='openpyxl'
            )
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={batch_id}_report.xlsx"}
            )

        # Group by gateway and transaction type
        dataframes = {}

        # Get unique gateways
        gateways = set(t.gateway for t in all_transactions)

        for gateway in gateways:
            gateway_txns = [t for t in all_transactions if t.gateway == gateway]

            # Group by transaction type
            types = set(t.transaction_type for t in gateway_txns)
            for txn_type in types:
                type_txns = [t for t in gateway_txns if t.transaction_type == txn_type]
                sheet_name = f"{gateway}_{txn_type}"
                dataframes[sheet_name] = transactions_to_dataframe(type_txns)

        # Write to Excel
        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        filename = f"full_{batch_id}_report.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception:
        raise


def download_batch_gateway_report(
    db_session: Session,
    batch_id: str,
    gateway: str,
    format: ReportFormat = "xlsx"
) -> StreamingResponse:
    """
    Generate and download reconciliation report for a specific batch and gateway.

    This is the primary report download function that generates a report with:
    - Date
    - Transaction Reference
    - Details
    - Debit
    - Credit
    - Reconciliation Status
    - Reconciliation Note
    - Reconciliation Key
    - Batch ID

    For Excel format, the report is split into multiple sheets:
    - {Gateway} External Debits: External debit transactions
    - Workpay {Gateway} Debits: Internal/workpay debit transactions
    - {Gateway} Credits Deposits: External credit/deposit transactions
    - {Gateway} Charges: Bank charges

    For CSV format, all transactions are in a single file.

    Args:
        db_session: Database session.
        batch_id: Batch ID to report on (must be a closed/completed batch).
        gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').
        format: Output format - 'xlsx' or 'csv'.

    Returns:
        StreamingResponse with the report file.

    Raises:
        ValueError: If no transactions found or invalid format.
    """
    gateway_lower = gateway.lower()
    gateway_display = gateway.capitalize()

    # Load all transactions for this batch and gateway
    transactions = load_transactions_for_gateway(db_session, batch_id, gateway_lower)

    if not transactions:
        raise ValueError(
            f"No transactions found for batch '{batch_id}' and gateway '{gateway}'"
        )

    # Generate filename
    base_filename = f"reconciliation_{gateway_lower}_{batch_id}"

    if format == "csv":
        # For CSV, generate a single flat file with all transactions
        df = transactions_to_report_dataframe(transactions)

        output = StringIO()
        df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
        output.seek(0)

        # Convert to bytes for streaming
        csv_bytes = BytesIO(output.getvalue().encode('utf-8'))

        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={base_filename}.csv"
            }
        )
    else:
        # For Excel, generate multi-sheet report
        # Separate transactions by type and source (external vs internal)
        external_debits = []
        internal_debits = []
        credits_deposits = []
        charges = []

        for txn in transactions:
            gateway_name = txn.gateway or ""
            txn_type = txn.transaction_type or ""

            # Determine if external or internal
            is_internal = (
                gateway_name.endswith("_internal") or
                gateway_name.startswith("workpay_")
            )

            if txn_type == TransactionType.CHARGE.value:
                charges.append(txn)
            elif txn_type == TransactionType.DEPOSIT.value:
                credits_deposits.append(txn)
            elif txn_type == TransactionType.DEBIT.value:
                if is_internal:
                    internal_debits.append(txn)
                else:
                    external_debits.append(txn)
            elif txn_type == TransactionType.PAYOUT.value:
                # Internal payouts go to internal debits sheet
                internal_debits.append(txn)

        # Build DataFrames for each sheet
        dataframes = {}

        if external_debits:
            dataframes[f"{gateway_display} External Debits"] = transactions_to_report_dataframe(external_debits)

        if internal_debits:
            dataframes[f"Workpay {gateway_display} Debits"] = transactions_to_report_dataframe(internal_debits)

        if credits_deposits:
            dataframes[f"{gateway_display} Credits Deposits"] = transactions_to_report_dataframe(credits_deposits)

        if charges:
            dataframes[f"{gateway_display} Charges"] = transactions_to_report_dataframe(charges)

        # If no categorized data (edge case), fall back to single sheet
        if not dataframes:
            dataframes = {"Transactions": transactions_to_report_dataframe(transactions)}

        # Write to Excel
        output = BytesIO()
        write_to_excel(output, dataframes)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={base_filename}.xlsx"
            }
        )