"""
Reconciliation Runs Controller.

Provides read-only endpoints for listing and viewing reconciliation runs.
Runs are auto-created when reconciliation is saved — no manual CRUD needed.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.sqlModels.runEntities import ReconciliationRun
from app.sqlModels.transactionEntities import Transaction
from app.sqlModels.authEntities import User
from app.auth.dependencies import require_active_user

router = APIRouter(prefix='/api/v1/runs', tags=['Reconciliation Runs'])


@router.get("")
async def list_runs(
    gateway: Optional[str] = Query(None, description="Filter by gateway"),
    date_from: Optional[str] = Query(None, description="Filter runs created from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter runs created to (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    List reconciliation runs with pagination and optional filters.

    Returns runs ordered by creation date (newest first).
    """
    query = select(ReconciliationRun)
    count_query = select(func.count()).select_from(ReconciliationRun)

    conditions = []

    if gateway:
        conditions.append(ReconciliationRun.gateway == gateway.lower().strip())

    if date_from:
        conditions.append(ReconciliationRun.created_at >= date_from)

    if date_to:
        conditions.append(ReconciliationRun.created_at <= date_to + " 23:59:59")

    if conditions:
        from sqlalchemy import and_
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_count = db.execute(count_query).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(ReconciliationRun.created_at)).offset(offset).limit(page_size)
    runs = db.execute(query).scalars().all()

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return JSONResponse(content={
        "runs": [
            {
                "id": r.id,
                "run_id": r.run_id,
                "gateway": r.gateway,
                "status": r.status,
                "total_external": r.total_external,
                "total_internal": r.total_internal,
                "matched": r.matched,
                "unmatched_external": r.unmatched_external,
                "unmatched_internal": r.unmatched_internal,
                "carry_forward_matched": r.carry_forward_matched,
                "created_by": r.created_by.username if r.created_by else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    })


@router.get("/{run_id}")
async def get_run(
    run_id: str = Path(..., description="Run ID"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get details of a single reconciliation run.

    Includes summary stats and transaction counts.
    """
    run = db.query(ReconciliationRun).filter(
        ReconciliationRun.run_id == run_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Count transactions for this run
    transaction_count = db.query(func.count(Transaction.id)).filter(
        Transaction.run_id == run_id
    ).scalar() or 0

    unreconciled_count = db.query(func.count(Transaction.id)).filter(
        Transaction.run_id == run_id,
        Transaction.reconciliation_status == "unreconciled",
    ).scalar() or 0

    return JSONResponse(content={
        "id": run.id,
        "run_id": run.run_id,
        "gateway": run.gateway,
        "status": run.status,
        "total_external": run.total_external,
        "total_internal": run.total_internal,
        "matched": run.matched,
        "unmatched_external": run.unmatched_external,
        "unmatched_internal": run.unmatched_internal,
        "carry_forward_matched": run.carry_forward_matched,
        "created_by": run.created_by.username if run.created_by else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "transaction_count": transaction_count,
        "unreconciled_count": unreconciled_count,
    })
