"""
Dashboard Controller.

Provides aggregated statistics and insights for the reconciliation dashboard.
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
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
    gateway: Optional[str] = Query(None, description="Filter by gateway (e.g., equity, kcb, mpesa)"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get comprehensive dashboard statistics.

    Returns aggregated transaction data including:
    - Wallet top-ups summary
    - Reconciled payouts (internal and external) with amounts and counts
    - Unreconciled payouts (internal and external) with amounts and counts
    - Additional insights (charges, credits, pending authorizations)

    Args:
        batch_id: Optional filter by specific batch.
        gateway: Optional filter by specific gateway.

    Returns:
        Dashboard statistics object.
    """
    # Base query filter
    filters = []
    if batch_id:
        filters.append(Transaction.batch_id == batch_id)
    if gateway:
        filters.append(Transaction.gateway == gateway.lower())

    # Helper to apply filters
    def apply_filters(query):
        if filters:
            return query.filter(and_(*filters))
        return query

    # ==========================================================================
    # 1. Wallet Top-Ups (transactions where manual_recon_note contains top-up keywords)
    # ==========================================================================
    topup_keywords = ['Wallet TopUp', 'Manual Topup', 'Bank Funding', 'MMF Funding']
    topup_conditions = or_(*[
        Transaction.manual_recon_note.ilike(f'%{kw}%') for kw in topup_keywords
    ])

    wallet_topups_query = apply_filters(
        db.query(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.debit), 0).label('debit_total'),
            func.coalesce(func.sum(Transaction.credit), 0).label('credit_total'),
        ).filter(topup_conditions)
    )
    wallet_topups = wallet_topups_query.first()

    wallet_topups_total = to_serializable(wallet_topups.debit_total) + \
                          to_serializable(wallet_topups.credit_total)

    # ==========================================================================
    # 2. External Payouts (Debits from external gateways - bank statements)
    # NOTE: Explicitly excludes CHARGE transactions - only counts DEBIT type
    # ==========================================================================

    # Reconciled external debits (excludes charges)
    reconciled_external = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('total'),
    ).filter(
        Transaction.transaction_type == TransactionType.DEBIT.value,  # Excludes CHARGE
        Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value
    )
    if filters:
        reconciled_external = reconciled_external.filter(and_(*filters))
    reconciled_external = reconciled_external.first()

    # Unreconciled external debits (excludes charges)
    unreconciled_external = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('total'),
    ).filter(
        Transaction.transaction_type == TransactionType.DEBIT.value,  # Excludes CHARGE
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value
    )
    if filters:
        unreconciled_external = unreconciled_external.filter(and_(*filters))
    unreconciled_external = unreconciled_external.first()

    # ==========================================================================
    # 3. Internal Payouts (from workpay records)
    # Uses debit + credit columns since unified template replaced amount column
    # ==========================================================================
    # Reconciled internal payouts
    reconciled_internal = db.query(
        func.count(Transaction.id).label('count'),
        (func.coalesce(func.sum(Transaction.debit), 0) +
         func.coalesce(func.sum(Transaction.credit), 0)).label('total'),
    ).filter(
        Transaction.transaction_type == TransactionType.PAYOUT.value,
        Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value
    )
    if filters:
        reconciled_internal = reconciled_internal.filter(and_(*filters))
    reconciled_internal = reconciled_internal.first()

    # Unreconciled internal payouts
    unreconciled_internal = db.query(
        func.count(Transaction.id).label('count'),
        (func.coalesce(func.sum(Transaction.debit), 0) +
         func.coalesce(func.sum(Transaction.credit), 0)).label('total'),
    ).filter(
        Transaction.transaction_type == TransactionType.PAYOUT.value,
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value
    )
    if filters:
        unreconciled_internal = unreconciled_internal.filter(and_(*filters))
    unreconciled_internal = unreconciled_internal.first()

    # ==========================================================================
    # 4. Additional Insights
    # ==========================================================================

    # Total credits (incoming funds)
    credits_query = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.credit), 0).label('total'),
    ).filter(Transaction.transaction_type == TransactionType.CREDIT.value)
    if filters:
        credits_query = credits_query.filter(and_(*filters))
    credits = credits_query.first()

    # Total charges (bank fees)
    charges_query = db.query(
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('total'),
    ).filter(Transaction.transaction_type == TransactionType.CHARGE.value)
    if filters:
        charges_query = charges_query.filter(and_(*filters))
    charges = charges_query.first()

    # Pending manual reconciliation authorizations
    pending_auth_query = db.query(
        func.count(Transaction.id).label('count'),
    ).filter(Transaction.authorization_status == AuthorizationStatus.PENDING.value)
    if filters:
        pending_auth_query = pending_auth_query.filter(and_(*filters))
    pending_auth = pending_auth_query.scalar() or 0

    # Manually reconciled and authorized
    manually_reconciled_query = db.query(
        func.count(Transaction.id).label('count'),
    ).filter(
        Transaction.is_manually_reconciled == "true",
        Transaction.authorization_status == AuthorizationStatus.AUTHORIZED.value
    )
    if filters:
        manually_reconciled_query = manually_reconciled_query.filter(and_(*filters))
    manually_reconciled = manually_reconciled_query.scalar() or 0

    # Total payout transactions (DEBIT + PAYOUT only, excludes CHARGE and CREDIT)
    total_payouts_query = db.query(func.count(Transaction.id)).filter(
        Transaction.transaction_type.in_([TransactionType.DEBIT.value, TransactionType.PAYOUT.value])
    )
    if filters:
        total_payouts_query = total_payouts_query.filter(and_(*filters))
    total_payouts = total_payouts_query.scalar() or 0

    # Reconciliation rate (percentage) - based on payouts only
    total_reconciled_payouts_query = db.query(func.count(Transaction.id)).filter(
        Transaction.transaction_type.in_([TransactionType.DEBIT.value, TransactionType.PAYOUT.value]),
        Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value
    )
    if filters:
        total_reconciled_payouts_query = total_reconciled_payouts_query.filter(and_(*filters))
    total_reconciled_payouts = total_reconciled_payouts_query.scalar() or 0

    reconciliation_rate = round((total_reconciled_payouts / total_payouts * 100), 2) if total_payouts > 0 else 0

    # ==========================================================================
    # 5. Breakdown by Gateway
    # ==========================================================================
    gateway_breakdown_query = db.query(
        Transaction.gateway,
        func.count(Transaction.id).label('total_count'),
        func.sum(case((Transaction.reconciliation_status == ReconciliationStatus.RECONCILED.value, 1), else_=0)).label('reconciled_count'),
        func.sum(case((Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value, 1), else_=0)).label('unreconciled_count'),
        func.coalesce(func.sum(Transaction.debit), 0).label('total_debit'),
        func.coalesce(func.sum(Transaction.credit), 0).label('total_credit'),
    ).group_by(Transaction.gateway)

    if filters:
        gateway_breakdown_query = gateway_breakdown_query.filter(and_(*filters))

    gateway_breakdown = [
        {
            "gateway": row.gateway,
            "total_count": int(row.total_count or 0),
            "reconciled_count": int(row.reconciled_count or 0),
            "unreconciled_count": int(row.unreconciled_count or 0),
            "total_debit": to_serializable(row.total_debit),
            "total_credit": to_serializable(row.total_credit),
            "total_amount": to_serializable(row.total_debit) + to_serializable(row.total_credit),
        }
        for row in gateway_breakdown_query.all()
    ]

    # ==========================================================================
    # 6. Get available filters (for dropdowns)
    # ==========================================================================
    available_batches = [
        {"batch_id": b.batch_id, "status": b.status}
        for b in db.query(Batch.batch_id, Batch.status).order_by(Batch.created_at.desc()).limit(50).all()
    ]

    available_gateways = [
        row[0] for row in db.query(Transaction.gateway).distinct().all()
    ]

    return JSONResponse(content={
        "filters": {
            "batch_id": batch_id,
            "gateway": gateway,
            "available_batches": available_batches,
            "available_gateways": available_gateways,
        },
        "wallet_topups": {
            "count": int(wallet_topups.count or 0),
            "total_amount": to_serializable(wallet_topups_total),
        },
        "reconciled": {
            "external": {
                "count": int(reconciled_external.count or 0),
                "amount": to_serializable(reconciled_external.total),
            },
            "internal": {
                "count": int(reconciled_internal.count or 0),
                "amount": to_serializable(reconciled_internal.total),
            },
        },
        "unreconciled": {
            "external": {
                "count": int(unreconciled_external.count or 0),
                "amount": to_serializable(unreconciled_external.total),
            },
            "internal": {
                "count": int(unreconciled_internal.count or 0),
                "amount": to_serializable(unreconciled_internal.total),
            },
        },
        "additional_insights": {
            "total_payouts": int(total_payouts or 0),
            "reconciliation_rate": float(reconciliation_rate),
            "credits": {
                "count": int(credits.count or 0),
                "amount": to_serializable(credits.total),
            },
            "charges": {
                "count": int(charges.count or 0),
                "amount": to_serializable(charges.total),
            },
            "pending_authorizations": int(pending_auth or 0),
            "manually_reconciled": int(manually_reconciled or 0),
        },
        "gateway_breakdown": gateway_breakdown,
    })
