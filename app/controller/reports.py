"""
Report download endpoints.

Provides endpoints for downloading reconciliation reports in Excel and CSV formats.

Reports are downloaded per batch and per gateway. Users must select:
1. A closed/completed batch
2. A specific gateway

Report columns:
- Date
- Transaction Reference
- Details
- Debit
- Credit
- Reconciliation Status
- Reconciliation Key
- Batch ID
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.reports.download_report import (
    download_gateway_report,
    download_full_report,
    download_batch_gateway_report,
)
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User
from app.sqlModels.batchEntities import Batch, BatchStatus
from app.config.gateways import get_external_gateways

router = APIRouter(prefix='/api/v1/reports', tags=['Report Endpoints'])


# =============================================================================
# Batch and Gateway Selection Endpoints
# =============================================================================

@router.get("/closed-batches")
async def get_closed_batches_for_reports(
    search: Optional[str] = Query(None, description="Search by batch ID"),
    limit: int = Query(5, ge=1, le=50, description="Number of batches to return"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get closed/completed batches for report generation.

    By default, returns the latest 5 closed batches. Use the search parameter
    to find a specific batch by its ID.

    Args:
        search: Optional batch ID search term.
        limit: Maximum number of batches to return (default: 5, max: 50).
        db: Database session.

    Returns:
        List of closed batches with their details.
    """
    query = select(Batch).where(Batch.status == BatchStatus.COMPLETED.value)

    if search:
        # Search by batch_id (partial match)
        search_term = f"%{search}%"
        query = query.where(Batch.batch_id.ilike(search_term))

    # Order by closed_at desc (most recent first), then created_at
    query = query.order_by(Batch.closed_at.desc(), Batch.created_at.desc()).limit(limit)

    batches = db.execute(query).scalars().all()

    # Get creator usernames
    from app.sqlModels.authEntities import User as UserModel
    result = []
    for batch in batches:
        creator = db.query(UserModel).filter(UserModel.id == batch.created_by_id).first()
        result.append({
            "batch_id": batch.batch_id,
            "batch_db_id": batch.id,
            "status": batch.status,
            "description": batch.description,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
            "created_by": creator.username if creator else None,
        })

    return JSONResponse(content={"batches": result, "count": len(result)})


@router.get("/available-gateways")
async def get_available_gateways_for_reports(
    batch_id: str = Query(..., description="Batch ID to check gateways for"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get gateways that have transactions in a specific batch.

    Only returns gateways that have at least one transaction in the batch.

    Args:
        batch_id: Batch ID to check.
        db: Database session.

    Returns:
        List of gateways with transaction counts.
    """
    from app.sqlModels.transactionEntities import Transaction
    from sqlalchemy import func

    # Get all external gateways from config
    external_gateways = get_external_gateways(db)

    # Count transactions per base gateway in this batch
    available = []
    for gw in external_gateways:
        # Count transactions matching this gateway pattern
        count = db.query(func.count(Transaction.id)).filter(
            Transaction.batch_id == batch_id,
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


# =============================================================================
# Report Download Endpoints
# =============================================================================

@router.get("/download/batch")
async def download_batch_report(
    batch_id: str = Query(..., description="Batch ID to generate report for"),
    gateway: str = Query(..., description="Gateway name (e.g., equity, kcb, mpesa)"),
    format: str = Query("xlsx", description="Report format: xlsx or csv"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Download reconciliation report for a specific batch and gateway.

    Both batch_id and gateway are required. The batch must be closed/completed.

    Report columns:
    - Date: Transaction date
    - Transaction Reference: Unique transaction identifier
    - Details: Transaction narration/description
    - Debit: Debit amount
    - Credit: Credit amount
    - Reconciliation Status: reconciled/unreconciled
    - Reconciliation Key: Composite key used for matching
    - Batch ID: Batch identifier

    Args:
        batch_id: Batch ID (must be a closed batch).
        gateway: Gateway name (e.g., equity, kcb, mpesa).
        format: Output format - 'xlsx' (default) or 'csv'.
        db: Database session.

    Returns:
        StreamingResponse: Report file download.

    Raises:
        HTTPException 400: If batch is not closed or gateway invalid.
        HTTPException 404: If batch not found.
        HTTPException 500: If report generation fails.
    """
    # Validate format
    format_lower = format.lower().strip()
    if format_lower not in ["xlsx", "csv"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Supported formats: xlsx, csv"
        )

    # Verify batch exists and is closed
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    if batch.status != BatchStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Batch '{batch_id}' is not closed. Only closed batches can be reported on."
        )

    # Validate gateway
    gateway_lower = gateway.lower().strip()
    external_gateways = get_external_gateways(db)

    if gateway_lower not in external_gateways:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gateway '{gateway}'. Available gateways: {external_gateways}"
        )

    try:
        return download_batch_gateway_report(db, batch_id, gateway_lower, format_lower)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )


# =============================================================================
# Legacy Endpoints (kept for backwards compatibility)
# =============================================================================

@router.get("/download/{gateway}")
async def download_gateway_reconciliation_report(
    gateway: str,
    batch_id: str = Query(..., description="Batch ID to generate report for"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Download reconciliation report for a specific payment gateway (legacy endpoint).

    NOTE: Use /download/batch endpoint instead for the new simplified report format.

    Generates an Excel report with the following sheets:
    - Summary: Reconciliation statistics
    - {gateway}_credits: Credit transactions
    - {gateway}_debits: Debit transactions
    - {gateway}_charges: Charge transactions
    - workpay_payouts: Internal payout records

    Args:
        gateway: Name of the gateway (equity, kcb, mpesa).
        batch_id: Batch ID containing reconciled transactions.
        db: Database session.

    Returns:
        StreamingResponse: Excel file download.

    Raises:
        HTTPException 400: If gateway is unsupported.
        HTTPException 500: If report generation fails.
    """
    try:
        gateway_lower = gateway.lower().strip()
        external_gateways = get_external_gateways(db)

        if gateway_lower not in external_gateways:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported gateway '{gateway}'. Supported: {external_gateways}"
            )

        return download_gateway_report(db, gateway_lower, batch_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading report for '{gateway}': {str(e)}"
        )


@router.get("/download")
async def download_full_reconciliation_report(
    batch_id: str = Query(..., description="Batch ID to generate report for"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Download full reconciliation report for all gateways (legacy endpoint).

    NOTE: Use /download/batch endpoint instead for the new simplified report format.

    Generates an Excel report with sheets for each gateway and transaction type
    combination found in the batch.

    Args:
        batch_id: Batch ID containing reconciled transactions.
        db: Database session.

    Returns:
        StreamingResponse: Excel file download.

    Raises:
        HTTPException 500: If report generation fails.
    """
    try:
        return download_full_report(db, batch_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading full report: {str(e)}"
        )
