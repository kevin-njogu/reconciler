"""
Dashboard Controller.

Provides aggregated statistics and insights for the reconciliation dashboard.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.sqlModels.transactionEntities import (
    Transaction,
    TransactionType,
    ReconciliationStatus,
    AuthorizationStatus,
)
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User
from app.config.gateways import get_gateway_display_name

router = APIRouter(prefix='/api/v1/dashboard', tags=['Dashboard'])


def to_serializable(value, default=0):
    """Convert Decimal/numeric values to JSON-serializable types."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get dashboard statistics with per-gateway tiles.

    Returns:
    - gateway_tiles: Per-gateway stats (counts, amounts, unreconciled)
    - summary: Overall reconciliation rate, pending authorizations, charges
    """
    # ======================================================================
    # 1. Discover base gateways with transactions
    # ======================================================================
    raw_gateways = [
        row[0] for row in db.query(Transaction.gateway).distinct().all() if row[0]
    ]
    base_gateways = sorted(set(
        Transaction.get_base_gateway(g) for g in raw_gateways
    ))

    # ======================================================================
    # 2. Per-gateway tiles
    # ======================================================================
    gateway_tiles = []
    total_reconciled_all = 0
    total_transactions_all = 0

    for base_gw in base_gateways:
        external_gw = f"{base_gw}_external"
        internal_gw = f"{base_gw}_internal"

        # External debits (DEBIT type only)
        ext_stats = db.query(
            func.count(Transaction.id).label('count'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value, 1),
                else_=0
            )).label('unreconciled'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value, 1),
                else_=0
            )).label('reconciled'),
        ).filter(
            Transaction.gateway == external_gw,
            Transaction.transaction_type == TransactionType.DEBIT.value,
        ).first()

        # Internal payouts (PAYOUT type)
        int_stats = db.query(
            func.count(Transaction.id).label('count'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value, 1),
                else_=0
            )).label('unreconciled'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value, 1),
                else_=0
            )).label('reconciled'),
        ).filter(
            Transaction.gateway == internal_gw,
            Transaction.transaction_type == TransactionType.PAYOUT.value,
        ).first()

        ext_count = int(ext_stats.count or 0)
        ext_unreconciled = int(ext_stats.unreconciled or 0)
        ext_reconciled = int(ext_stats.reconciled or 0)

        int_count = int(int_stats.count or 0)
        int_unreconciled = int(int_stats.unreconciled or 0)
        int_reconciled = int(int_stats.reconciled or 0)

        unreconciled_total = ext_unreconciled + int_unreconciled
        reconciled_total = ext_reconciled + int_reconciled
        total_count = ext_count + int_count
        matching_pct = round((reconciled_total / total_count * 100), 1) if total_count > 0 else 0.0
        total_reconciled_all += reconciled_total
        total_transactions_all += total_count

        gateway_tiles.append({
            "base_gateway": base_gw,
            "display_name": get_gateway_display_name(base_gw, db),
            "external_debit_count": ext_count,
            "internal_payout_count": int_count,
            "unreconciled_count": unreconciled_total,
            "matching_percentage": float(matching_pct),
        })

    # ======================================================================
    # 3. Summary stats
    # ======================================================================
    reconciliation_rate = (
        round((total_reconciled_all / total_transactions_all * 100), 1)
        if total_transactions_all > 0 else 0.0
    )

    # Pending authorizations
    pending_auth = db.query(func.count(Transaction.id)).filter(
        Transaction.authorization_status == AuthorizationStatus.PENDING.value
    ).scalar() or 0

    # Total unreconciled items across all gateways (count + sum of amounts)
    unreconciled = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('amount'),
    ).filter(
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value,
    ).first()

    # ======================================================================
    # 4. Build response
    # ======================================================================
    return JSONResponse(content={
        "gateway_tiles": gateway_tiles,
        "summary": {
            "reconciliation_rate": float(reconciliation_rate),
            "pending_authorizations": int(pending_auth or 0),
            "unreconciled_count": int(unreconciled.count or 0),
            "unreconciled_amount": to_serializable(unreconciled.amount),
        },
    })
