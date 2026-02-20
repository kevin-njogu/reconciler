"""
Report generation for reconciliation results.

Generates Excel and CSV reports from the unified transactions table.

Report Columns:
- Date
- Transaction Reference
- Details
- Debit
- Credit
- Reconciliation Status
- Reconciliation Note
- Reconciliation Key
- Run ID

Excel Format Sheets:
- Unreconciled External: Unmatched external (bank) debits
- Unreconciled Internal: Unmatched internal (Workpay) payouts
- Reconciled External: Matched external (bank) debits
- Reconciled Internal: Matched internal (Workpay) payouts
- Manual External: Manually reconciled external transactions
- Manual Internal: Manually reconciled internal transactions
- Charges: Bank charges (auto-reconciled)
- Deposits: Credit/deposit transactions (auto-reconciled)
"""
import csv
import logging
from collections import Counter
from datetime import date
from io import BytesIO, StringIO
from typing import Optional, List, Literal

import pandas as pd
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.reports.output_writer import write_to_excel
from app.sqlModels.transactionEntities import Transaction, TransactionType, ReconciliationStatus

logger = logging.getLogger("app.reports")


# Report format types
ReportFormat = Literal["xlsx", "csv"]


def load_transactions_for_gateway(
    db_session: Session,
    base_gateway: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    run_id: Optional[str] = None,
) -> List[Transaction]:
    """
    Load all transactions for a base gateway (both external and internal).

    Args:
        db_session: Database session.
        base_gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').
        date_from: Optional start date filter.
        date_to: Optional end date filter.
        run_id: Optional run ID filter.

    Returns:
        List of Transaction records for both external and internal.
    """
    base_lower = base_gateway.lower()

    conditions = [
        or_(
            Transaction.gateway == base_lower,
            Transaction.gateway == f"{base_lower}_external",
            Transaction.gateway == f"{base_lower}_internal",
            Transaction.gateway.endswith(f"_{base_lower}")
        )
    ]

    if run_id:
        conditions.append(Transaction.run_id == run_id)
    if date_from:
        conditions.append(Transaction.date >= date_from)
    if date_to:
        conditions.append(Transaction.date <= date_to)

    stmt = (
        select(Transaction)
        .where(and_(*conditions))
        .order_by(Transaction.date, Transaction.id)
    )

    return db_session.execute(stmt).scalars().all()


def transactions_to_report_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """
    Convert transaction records to report DataFrame with required columns.

    Columns: Date, Transaction Reference, Details, Debit, Credit,
             Reconciliation Status, Reconciliation Note, Reconciliation Key, Run ID
    """
    if not transactions:
        return pd.DataFrame(columns=[
            "Date", "Transaction Reference", "Details", "Debit", "Credit",
            "Reconciliation Status", "Reconciliation Note", "Reconciliation Key", "Run ID"
        ])

    records = []
    for t in transactions:
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
            "Run ID": t.run_id or "",
        })

    return pd.DataFrame(records)


def download_gateway_report_filtered(
    db_session: Session,
    gateway: str,
    format: ReportFormat = "xlsx",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    run_id: Optional[str] = None,
) -> StreamingResponse:
    """
    Generate and download reconciliation report for a specific gateway.

    Args:
        db_session: Database session.
        gateway: Base gateway name (e.g., 'equity', 'kcb', 'mpesa').
        format: Output format - 'xlsx' or 'csv'.
        date_from: Optional start date filter.
        date_to: Optional end date filter.
        run_id: Optional run ID filter.

    Returns:
        StreamingResponse with the report file.

    Raises:
        ValueError: If no transactions found.
    """
    gateway_lower = gateway.lower()
    gateway_display = gateway.capitalize()

    # Load transactions with filters
    transactions = load_transactions_for_gateway(
        db_session, gateway_lower,
        date_from=date_from,
        date_to=date_to,
        run_id=run_id,
    )

    if not transactions:
        filter_desc = f"gateway '{gateway}'"
        if date_from:
            filter_desc += f" from {date_from}"
        if date_to:
            filter_desc += f" to {date_to}"
        if run_id:
            filter_desc += f" run {run_id}"
        raise ValueError(f"No transactions found for {filter_desc}")

    # Log loaded transactions breakdown for diagnostics
    gw_counts = Counter(t.gateway for t in transactions)
    type_counts = Counter(t.transaction_type for t in transactions)
    logger.info(
        f"Report for '{gateway}': loaded {len(transactions)} transactions. "
        f"By gateway: {dict(gw_counts)}. By type: {dict(type_counts)}"
    )

    # Generate filename
    parts = [f"reconciliation_{gateway_lower}"]
    if date_from:
        parts.append(f"from_{date_from.isoformat()}")
    if date_to:
        parts.append(f"to_{date_to.isoformat()}")
    if run_id:
        parts.append(run_id)
    base_filename = "_".join(parts)

    if format == "csv":
        # Single flat CSV file
        df = transactions_to_report_dataframe(transactions)

        output = StringIO()
        df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
        output.seek(0)

        csv_bytes = BytesIO(output.getvalue().encode('utf-8'))

        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={base_filename}.csv"
            }
        )
    else:
        # Multi-sheet Excel report: 8 sheets split by side, reconciliation status, and manual
        unreconciled_external = []
        unreconciled_internal = []
        reconciled_external = []
        reconciled_internal = []
        manual_external = []
        manual_internal = []
        charges = []
        deposits = []

        for txn in transactions:
            gateway_name = txn.gateway or ""
            txn_type = txn.transaction_type or ""
            recon_status = txn.reconciliation_status or ""
            is_manual = txn.is_manually_reconciled == "true"

            is_internal = (
                gateway_name.endswith("_internal") or
                gateway_name.startswith("workpay_")
            )
            is_reconciled = recon_status == ReconciliationStatus.RECONCILED.value

            if txn_type == TransactionType.CHARGE.value:
                charges.append(txn)
            elif txn_type == TransactionType.DEPOSIT.value:
                deposits.append(txn)
            elif is_manual:
                if is_internal:
                    manual_internal.append(txn)
                else:
                    manual_external.append(txn)
            elif is_internal:
                if is_reconciled:
                    reconciled_internal.append(txn)
                else:
                    unreconciled_internal.append(txn)
            else:
                if is_reconciled:
                    reconciled_external.append(txn)
                else:
                    unreconciled_external.append(txn)

        logger.info(
            f"Report sheet breakdown: "
            f"Unreconciled External={len(unreconciled_external)}, "
            f"Unreconciled Internal={len(unreconciled_internal)}, "
            f"Reconciled External={len(reconciled_external)}, "
            f"Reconciled Internal={len(reconciled_internal)}, "
            f"Manual External={len(manual_external)}, "
            f"Manual Internal={len(manual_internal)}, "
            f"Charges={len(charges)}, Deposits={len(deposits)}"
        )

        # Always create all 8 sheets (empty DataFrame if no data for that category)
        dataframes = {
            "Unreconciled External": transactions_to_report_dataframe(unreconciled_external),
            "Unreconciled Internal": transactions_to_report_dataframe(unreconciled_internal),
            "Reconciled External": transactions_to_report_dataframe(reconciled_external),
            "Reconciled Internal": transactions_to_report_dataframe(reconciled_internal),
            "Manual External": transactions_to_report_dataframe(manual_external),
            "Manual Internal": transactions_to_report_dataframe(manual_internal),
            "Charges": transactions_to_report_dataframe(charges),
            "Deposits": transactions_to_report_dataframe(deposits),
        }

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
