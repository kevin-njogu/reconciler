"""
Dashboard Controller.

Provides aggregated statistics and insights for the reconciliation dashboard.
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.sqlModels.transactionEntities import (
    Transaction,
    TransactionType,
    ReconciliationStatus,
    AuthorizationStatus,
)
from app.sqlModels.batchEntities import Batch
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
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    gateway: Optional[str] = Query(None, description="Filter by base gateway (e.g., equity, kcb, mpesa)"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get dashboard statistics with per-gateway tiles.

    Returns:
    - latest_batch_id: Most recent batch for auto-selection
    - gateway_tiles: Per-base-gateway stats (external/internal debit counts, matching %, unreconciled)
    - batch_charges: Batch-wide charge totals (all gateways)
    - pending_authorizations: Batch-wide pending authorization count
    - summary: Batch-level reconciliation rate, manually reconciled
    """
    # ======================================================================
    # 1. Latest batch for auto-selection
    # ======================================================================
    latest_batch = db.query(Batch.batch_id).order_by(Batch.created_at.desc()).first()
    latest_batch_id = latest_batch.batch_id if latest_batch else None

    # Batch filter (used for most queries)
    batch_filter = [Transaction.batch_id == batch_id] if batch_id else []

    # ======================================================================
    # 2. Discover base gateways with transactions in this batch
    # ======================================================================
    gw_query = db.query(Transaction.gateway).distinct()
    if batch_id:
        gw_query = gw_query.filter(Transaction.batch_id == batch_id)
    raw_gateways = [row[0] for row in gw_query.all() if row[0]]
    base_gateways = sorted(set(
        Transaction.get_base_gateway(g) for g in raw_gateways
    ))

    # If gateway filter is provided, restrict to that single gateway
    if gateway:
        gateway_lower = gateway.lower()
        base_gateways = [gw for gw in base_gateways if gw == gateway_lower]

    # ======================================================================
    # 3. Per-gateway tiles
    # ======================================================================
    gateway_tiles = []
    for base_gw in base_gateways:
        external_gw = f"{base_gw}_external"
        internal_gw = f"{base_gw}_internal"

        # External debits (DEBIT type only, excludes CHARGE)
        ext_stats = db.query(
            func.count(Transaction.id).label('total'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value, 1),
                else_=0
            )).label('reconciled'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value, 1),
                else_=0
            )).label('unreconciled'),
        ).filter(
            Transaction.gateway == external_gw,
            Transaction.transaction_type == TransactionType.DEBIT.value,
            *batch_filter
        ).first()

        # Internal payouts (PAYOUT type)
        int_stats = db.query(
            func.count(Transaction.id).label('total'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value, 1),
                else_=0
            )).label('reconciled'),
            func.sum(case(
                (Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value, 1),
                else_=0
            )).label('unreconciled'),
        ).filter(
            Transaction.gateway == internal_gw,
            Transaction.transaction_type == TransactionType.PAYOUT.value,
            *batch_filter
        ).first()

        ext_debit_count = int(ext_stats.total or 0)
        int_debit_count = int(int_stats.total or 0)
        reconciled_count = int(ext_stats.reconciled or 0)
        unreconciled_ext = int(ext_stats.unreconciled or 0)
        unreconciled_int = int(int_stats.unreconciled or 0)

        matching_pct = round((reconciled_count / ext_debit_count * 100), 2) if ext_debit_count > 0 else 0.0

        gateway_tiles.append({
            "base_gateway": base_gw,
            "display_name": get_gateway_display_name(base_gw, db),
            "external_debit_count": ext_debit_count,
            "internal_debit_count": int_debit_count,
            "reconciled_debit_count": reconciled_count,
            "unreconciled_count": unreconciled_ext + unreconciled_int,
            "matching_percentage": float(matching_pct),
        })

    # ======================================================================
    # 4. Batch-wide charges (all gateways, only filtered by batch)
    # ======================================================================
    charges_filters = [Transaction.transaction_type == TransactionType.CHARGE.value]
    if batch_id:
        charges_filters.append(Transaction.batch_id == batch_id)

    charges = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('total'),
    ).filter(*charges_filters).first()

    # ======================================================================
    # 5. Batch-wide pending authorizations (only filtered by batch)
    # ======================================================================
    pending_filters = [Transaction.authorization_status == AuthorizationStatus.PENDING.value]
    if batch_id:
        pending_filters.append(Transaction.batch_id == batch_id)

    pending_auth = db.query(func.count(Transaction.id)).filter(*pending_filters).scalar() or 0

    # ======================================================================
    # 6. Summary stats (batch-level, not gateway-filtered)
    # ======================================================================
    # Total reconciled payout transactions (DEBIT + PAYOUT)
    payout_types = [TransactionType.DEBIT.value, TransactionType.PAYOUT.value]

    total_payouts_query = db.query(func.count(Transaction.id)).filter(
        Transaction.transaction_type.in_(payout_types)
    )
    if batch_id:
        total_payouts_query = total_payouts_query.filter(Transaction.batch_id == batch_id)
    total_payouts = total_payouts_query.scalar() or 0

    reconciled_payouts_query = db.query(func.count(Transaction.id)).filter(
        Transaction.transaction_type.in_(payout_types),
        Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value
    )
    if batch_id:
        reconciled_payouts_query = reconciled_payouts_query.filter(Transaction.batch_id == batch_id)
    total_reconciled = reconciled_payouts_query.scalar() or 0

    total_unreconciled = total_payouts - total_reconciled
    reconciliation_rate = round((total_reconciled / total_payouts * 100), 2) if total_payouts > 0 else 0.0

    # Manually reconciled and authorized
    manually_query = db.query(func.count(Transaction.id)).filter(
        Transaction.is_manually_reconciled == "true",
        Transaction.authorization_status == AuthorizationStatus.AUTHORIZED.value
    )
    if batch_id:
        manually_query = manually_query.filter(Transaction.batch_id == batch_id)
    manually_reconciled = manually_query.scalar() or 0

    # ======================================================================
    # 7. Build response
    # ======================================================================
    return JSONResponse(content={
        "latest_batch_id": latest_batch_id,
        "gateway_tiles": gateway_tiles,
        "batch_charges": {
            "count": int(charges.count or 0),
            "amount": to_serializable(charges.total),
        },
        "pending_authorizations": int(pending_auth or 0),
        "summary": {
            "total_reconciled": int(total_reconciled),
            "total_unreconciled": int(total_unreconciled),
            "reconciliation_rate": float(reconciliation_rate),
            "manually_reconciled": int(manually_reconciled),
        },
    })
