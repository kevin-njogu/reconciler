"""
Transactions controller.

Provides endpoints for listing and searching all transactions.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from app.database.mysql_configs import get_database
from app.sqlModels.transactionEntities import Transaction
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User


router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


def transaction_to_dict(txn: Transaction) -> dict:
    """Convert Transaction model to response dict.

    Returns the essential columns:
    - date: Transaction date
    - transaction_id: Transaction reference
    - reconciliation_key: Composite key for matching
    - run_id: Reconciliation run identifier
    - gateway: Gateway name
    - amount: Debit or credit amount (whichever is non-zero)
    - reconciliation_status: reconciled/unreconciled
    - transaction_type: Type of transaction (debit, credit, charge)
    """
    # Determine the amount (use debit if present, otherwise credit)
    amount = None
    if txn.debit and float(txn.debit) > 0:
        amount = float(txn.debit)
    elif txn.credit and float(txn.credit) > 0:
        amount = float(txn.credit)

    return {
        "id": txn.id,
        "date": txn.date.isoformat() if txn.date else None,
        "transaction_id": txn.transaction_id,
        "reconciliation_key": txn.reconciliation_key,
        "run_id": txn.run_id,
        "gateway": txn.gateway,
        "amount": amount,
        "reconciliation_status": txn.reconciliation_status,
        "transaction_type": txn.transaction_type,
    }


@router.get("")
def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by transaction ID"),
    gateway: Optional[str] = Query(None, description="Filter by gateway"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    reconciliation_status: Optional[str] = Query(None, description="Filter by status"),
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    List all transactions with pagination and filters.

    Supports:
    - Pagination (page, page_size)
    - Search by transaction ID (partial match)
    - Filter by gateway, run_id, date range, reconciliation_status, transaction_type
    """
    # Build query conditions
    conditions = []

    if search:
        # Search by transaction ID (case-insensitive partial match)
        conditions.append(Transaction.transaction_id.ilike(f"%{search}%"))

    if gateway:
        # Support base gateway filtering (e.g., "equity" matches "equity_external" and "equity_internal")
        gateway_lower = gateway.lower()
        conditions.append(
            or_(
                Transaction.gateway == gateway_lower,
                Transaction.gateway == f"{gateway_lower}_external",
                Transaction.gateway == f"{gateway_lower}_internal",
            )
        )

    if run_id:
        conditions.append(Transaction.run_id == run_id)

    if date_from:
        from datetime import date
        try:
            conditions.append(Transaction.date >= date.fromisoformat(date_from))
        except ValueError:
            pass

    if date_to:
        from datetime import date
        try:
            conditions.append(Transaction.date <= date.fromisoformat(date_to))
        except ValueError:
            pass

    if reconciliation_status:
        conditions.append(Transaction.reconciliation_status == reconciliation_status.lower())

    if transaction_type:
        conditions.append(Transaction.transaction_type == transaction_type.lower())

    # Base query
    base_query = select(Transaction)
    if conditions:
        base_query = base_query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Transaction)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_count = db.execute(count_query).scalar()

    # Get paginated results (ordered by created_at desc, then id desc)
    offset = (page - 1) * page_size
    paginated_query = (
        base_query
        .order_by(desc(Transaction.created_at), desc(Transaction.id))
        .offset(offset)
        .limit(page_size)
    )
    transactions = db.execute(paginated_query).scalars().all()

    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return {
        "transactions": [transaction_to_dict(t) for t in transactions],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }


@router.get("/filters")
def get_filter_options(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get available filter options for transactions.

    Returns unique values for gateways, run IDs, statuses, and types.
    """
    # Get unique gateways
    gateways_query = select(Transaction.gateway).distinct()
    gateways = [row[0] for row in db.execute(gateways_query).all() if row[0]]

    # Get unique run IDs (limit to recent 50)
    run_ids_query = (
        select(Transaction.run_id)
        .distinct()
        .order_by(desc(Transaction.run_id))
        .limit(50)
    )
    run_ids = [row[0] for row in db.execute(run_ids_query).all() if row[0]]

    # Get unique reconciliation statuses
    statuses_query = select(Transaction.reconciliation_status).distinct()
    statuses = [row[0] for row in db.execute(statuses_query).all() if row[0]]

    # Get unique transaction types
    types_query = select(Transaction.transaction_type).distinct()
    types = [row[0] for row in db.execute(types_query).all() if row[0]]

    return {
        "gateways": sorted(gateways),
        "run_ids": run_ids,
        "reconciliation_statuses": sorted(statuses),
        "transaction_types": sorted(types),
    }


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get a single transaction by its database ID.
    """
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    txn = db.execute(stmt).scalar_one_or_none()

    if not txn:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction_to_dict(txn)
