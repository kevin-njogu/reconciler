"""
Report download endpoints.

Provides endpoints for downloading reconciliation reports in Excel and CSV formats.

Reports are per-gateway with optional date range and run_id filters.

Report columns:
- Date
- Transaction Reference
- Details
- Debit
- Credit
- Reconciliation Status
- Reconciliation Note
- Reconciliation Key
- Run ID
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.reports.download_report import (
    download_gateway_report_filtered,
)
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User
from app.sqlModels.transactionEntities import Transaction
from app.sqlModels.runEntities import ReconciliationRun
from app.config.gateways import get_external_gateways

router = APIRouter(prefix='/api/v1/reports', tags=['Report Endpoints'])


# =============================================================================
# Gateway Selection Endpoints
# =============================================================================

@router.get("/available-gateways")
async def get_available_gateways_for_reports(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get gateways that have transactions in the database.

    Returns gateways with transaction counts for report generation.
    """
    external_gateways = get_external_gateways(db)

    available = []
    for gw in external_gateways:
        count = db.query(func.count(Transaction.id)).filter(
            or_(
                Transaction.gateway == gw,
                Transaction.gateway == f"{gw}_external",
                Transaction.gateway == f"{gw}_internal",
                Transaction.gateway.endswith(f"_{gw}")
            )
        ).scalar()

        if count > 0:
            available.append({
                "gateway": gw,
                "display_name": gw.upper(),
                "transaction_count": count,
            })

    return JSONResponse(content={"gateways": available, "count": len(available)})


@router.get("/runs")
async def get_runs_for_reports(
    gateway: Optional[str] = Query(None, description="Filter by gateway"),
    limit: int = Query(20, ge=1, le=100, description="Number of runs to return"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get reconciliation runs for report drill-down.

    Returns runs for optional filtering when downloading reports.
    """
    query = db.query(ReconciliationRun)

    if gateway:
        query = query.filter(ReconciliationRun.gateway == gateway.lower().strip())

    runs = query.order_by(ReconciliationRun.created_at.desc()).limit(limit).all()

    return JSONResponse(content={
        "runs": [
            {
                "run_id": r.run_id,
                "gateway": r.gateway,
                "matched": r.matched,
                "unmatched_external": r.unmatched_external,
                "unmatched_internal": r.unmatched_internal,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "count": len(runs),
    })


# =============================================================================
# Report Download Endpoints
# =============================================================================

@router.get("/download")
async def download_report(
    gateway: str = Query(..., description="Gateway name (e.g., equity, kcb, mpesa)"),
    format: str = Query("xlsx", description="Report format: xlsx or csv"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    run_id: Optional[str] = Query(None, description="Filter by specific run ID"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Download reconciliation report for a specific gateway.

    Required: gateway. Optional: date range and run_id filters.

    Report columns:
    - Date, Transaction Reference, Details, Debit, Credit
    - Reconciliation Status, Reconciliation Note, Reconciliation Key, Run ID

    For Excel format, the report is split into 6 sheets:
    - Unreconciled External (unmatched bank debits)
    - Unreconciled Internal (unmatched Workpay payouts)
    - Reconciled External (matched bank debits)
    - Reconciled Internal (matched Workpay payouts)
    - Charges (bank charges, auto-reconciled)
    - Deposits (credits/deposits, auto-reconciled)
    """
    # Validate format
    format_lower = format.lower().strip()
    if format_lower not in ["xlsx", "csv"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Supported formats: xlsx, csv"
        )

    # Validate gateway
    gateway_lower = gateway.lower().strip()
    external_gateways = get_external_gateways(db)

    if gateway_lower not in external_gateways:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gateway '{gateway}'. Available gateways: {external_gateways}"
        )

    # Parse dates
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = date.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from}. Use YYYY-MM-DD.")
    if date_to:
        try:
            parsed_date_to = date.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to}. Use YYYY-MM-DD.")

    try:
        return download_gateway_report_filtered(
            db, gateway_lower, format_lower,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            run_id=run_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )
