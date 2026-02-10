"""
Operations Controller.

Handles manual reconciliation and authorization workflows:
- List unreconciled transactions by gateway
- Manual reconciliation by users
- Authorization by admins
"""
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from starlette.responses import JSONResponse
from pydantic import BaseModel

from app.database.mysql_configs import get_database
from app.sqlModels.transactionEntities import (
    Transaction,
    TransactionType,
    ReconciliationStatus,
    AuthorizationStatus,
)
from app.sqlModels.authEntities import User, AuditLog
from app.auth.dependencies import require_active_user, require_admin_only, require_user_role
from app.config.gateways import get_external_gateways

router = APIRouter(prefix='/api/v1/operations', tags=['Operations'])


# ============================================================================
# Pydantic Models
# ============================================================================

class ManualReconciliationRequest(BaseModel):
    transaction_type: str
    note: str


class AuthorizationRequest(BaseModel):
    action: str  # 'authorize' or 'reject'
    note: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def transaction_to_response(txn: Transaction) -> dict:
    """Convert Transaction model to response dict."""
    return {
        "id": txn.id,
        "gateway": txn.gateway,
        "transaction_type": txn.transaction_type,
        "date": txn.date.isoformat() if txn.date else None,
        "transaction_id": txn.transaction_id,
        "narrative": txn.narrative,
        "debit": float(txn.debit) if txn.debit else None,
        "credit": float(txn.credit) if txn.credit else None,
        "reconciliation_status": txn.reconciliation_status,
        "reconciliation_key": txn.reconciliation_key,
        "run_id": txn.run_id,
        "is_manually_reconciled": txn.is_manually_reconciled,
        "manual_recon_note": txn.manual_recon_note,
        "manual_recon_by": txn.manual_recon_by,
        "manual_recon_by_username": (
            txn.manual_reconciled_user.username
            if txn.manual_reconciled_user else None
        ),
        "manual_recon_at": txn.manual_recon_at.isoformat() if txn.manual_recon_at else None,
        "authorization_status": txn.authorization_status,
        "authorized_by": txn.authorized_by,
        "authorized_by_username": (
            txn.authorization_user.username
            if txn.authorization_user else None
        ),
        "authorized_at": txn.authorized_at.isoformat() if txn.authorized_at else None,
        "authorization_note": txn.authorization_note,
    }


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/unreconciled")
async def get_unreconciled_transactions(
    gateway: Optional[str] = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get all unreconciled transactions, optionally filtered by gateway.

    This returns transactions that are:
    - Status is 'unreconciled'
    - NOT already pending authorization (already manually reconciled awaiting approval)
    - NOT already authorized

    Args:
        gateway: Optional gateway filter (e.g., 'equity', 'kcb', 'mpesa').

    Returns:
        List of unreconciled transactions grouped by gateway.
    """
    # Build query
    query = db.query(Transaction).filter(
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value,
        # Exclude transactions already pending authorization or authorized
        or_(
            Transaction.authorization_status.is_(None),
            Transaction.authorization_status == AuthorizationStatus.REJECTED.value
        )
    )

    if gateway:
        # Support both full gateway names (e.g., "mpesa_external") and base names (e.g., "mpesa")
        gateway_lower = gateway.lower()
        if gateway_lower.endswith('_external') or gateway_lower.endswith('_internal'):
            # Full gateway name - exact match
            query = query.filter(Transaction.gateway == gateway_lower)
        else:
            # Base gateway name - match both _external and _internal variants
            query = query.filter(
                or_(
                    Transaction.gateway == f"{gateway_lower}_external",
                    Transaction.gateway == f"{gateway_lower}_internal"
                )
            )

    transactions = query.order_by(Transaction.date.desc()).all()

    # Group by gateway
    grouped = {}
    for txn in transactions:
        gw = txn.gateway
        if gw not in grouped:
            grouped[gw] = []
        grouped[gw].append(transaction_to_response(txn))

    # Get available gateways (only those with unreconciled transactions)
    gateway_query = db.query(Transaction.gateway).filter(
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value,
        # Exclude transactions already pending authorization
        or_(
            Transaction.authorization_status.is_(None),
            Transaction.authorization_status == AuthorizationStatus.REJECTED.value
        )
    ).distinct().all()
    available_gateways = [g[0] for g in gateway_query]

    return JSONResponse(content={
        "gateway_filter": gateway,
        "available_gateways": available_gateways,
        "total_count": len(transactions),
        "by_gateway": grouped,
    })


@router.get("/pending-authorization")
async def get_pending_authorization(
    gateway: Optional[str] = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Get all transactions pending authorization (checker operation).

    Only admins (not super_admins) can view pending authorizations.
    These are transactions that have been manually reconciled by users
    and are awaiting admin approval.

    Args:
        gateway: Optional gateway filter.

    Returns:
        List of transactions pending authorization.
    """
    query = db.query(Transaction).filter(
        Transaction.authorization_status == AuthorizationStatus.PENDING.value
    )

    if gateway:
        # Support both full gateway names (e.g., "mpesa_external") and base names (e.g., "mpesa")
        gateway_lower = gateway.lower()
        if gateway_lower.endswith('_external') or gateway_lower.endswith('_internal'):
            # Full gateway name - exact match
            query = query.filter(Transaction.gateway == gateway_lower)
        else:
            # Base gateway name - match both _external and _internal variants
            query = query.filter(
                or_(
                    Transaction.gateway == f"{gateway_lower}_external",
                    Transaction.gateway == f"{gateway_lower}_internal"
                )
            )

    transactions = query.order_by(Transaction.manual_recon_at.desc()).all()

    # Group by gateway
    grouped = {}
    for txn in transactions:
        gw = txn.gateway
        if gw not in grouped:
            grouped[gw] = {
                "gateway": gw,
                "transactions": []
            }
        grouped[gw]["transactions"].append(transaction_to_response(txn))

    return JSONResponse(content={
        "total_count": len(transactions),
        "groups": list(grouped.values()),
    })


@router.post("/manual-reconcile/{transaction_id}")
async def manual_reconcile(
    transaction_id: int,
    request_body: ManualReconciliationRequest,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Manually reconcile a transaction.

    This marks the transaction as manually reconciled with a note explaining
    the reason. The transaction is then placed in 'pending' authorization
    status for admin approval.

    Args:
        transaction_id: The transaction ID to reconcile.
        request_body: Contains the reconciliation note.

    Returns:
        Updated transaction details.
    """
    # Get the transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate transaction is unreconciled
    if transaction.reconciliation_status != ReconciliationStatus.UNRECONCILED.value:
        raise HTTPException(
            status_code=400,
            detail="Transaction is already reconciled"
        )

    # Check if already pending authorization
    if transaction.authorization_status == AuthorizationStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Transaction is already pending authorization"
        )

    # Validate transaction_type
    valid_types = [t.value for t in TransactionType]
    if request_body.transaction_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}"
        )

    # Update transaction
    transaction.transaction_type = request_body.transaction_type
    transaction.is_manually_reconciled = "true"
    transaction.manual_recon_note = request_body.note
    transaction.manual_recon_by = current_user.id
    transaction.manual_recon_at = datetime.now(ZoneInfo("Africa/Nairobi"))
    transaction.authorization_status = AuthorizationStatus.PENDING.value

    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="manual_reconcile",
        resource_type="transaction",
        resource_id=str(transaction_id),
        details={
            "run_id": transaction.run_id,
            "gateway": transaction.gateway,
            "transaction_id": transaction.transaction_id,
            "transaction_type": request_body.transaction_type,
            "note": request_body.note,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_path=request.url.path,
        request_method="POST",
    )
    db.add(audit_log)
    db.commit()
    db.refresh(transaction)

    return JSONResponse(content={
        "message": "Transaction manually reconciled and pending authorization",
        "transaction": transaction_to_response(transaction),
    })


class BulkManualReconciliationRequest(BaseModel):
    transaction_ids: List[int]
    transaction_type: str
    note: str


@router.post("/manual-reconcile-bulk")
async def manual_reconcile_bulk(
    request_body: BulkManualReconciliationRequest,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Manually reconcile multiple transactions at once (user role only).

    This marks multiple transactions as manually reconciled with a common note.
    All transactions are placed in 'pending' authorization status for admin approval.

    Args:
        request_body: Contains transaction_ids list and the reconciliation note.

    Returns:
        Summary of reconciled transactions.
    """
    transaction_ids = request_body.transaction_ids
    note = request_body.note

    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")

    if not note or not note.strip():
        raise HTTPException(status_code=400, detail="Reconciliation note is required")

    # Validate transaction_type
    valid_types = [t.value for t in TransactionType]
    if request_body.transaction_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}"
        )

    # Get eligible transactions (unreconciled and not already pending)
    transactions = db.query(Transaction).filter(
        Transaction.id.in_(transaction_ids),
        Transaction.reconciliation_status == ReconciliationStatus.UNRECONCILED.value,
        or_(
            Transaction.authorization_status.is_(None),
            Transaction.authorization_status == AuthorizationStatus.REJECTED.value
        )
    ).all()

    if not transactions:
        raise HTTPException(
            status_code=404,
            detail="No eligible transactions found. Transactions must be unreconciled and not already pending authorization."
        )

    # Update all transactions
    now = datetime.now(ZoneInfo("Africa/Nairobi"))
    for txn in transactions:
        txn.transaction_type = request_body.transaction_type
        txn.is_manually_reconciled = "true"
        txn.manual_recon_note = note.strip()
        txn.manual_recon_by = current_user.id
        txn.manual_recon_at = now
        txn.authorization_status = AuthorizationStatus.PENDING.value

    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="bulk_manual_reconcile",
        resource_type="transaction",
        resource_id=f"bulk:{len(transactions)}",
        details={
            "transaction_type": request_body.transaction_type,
            "note": note.strip(),
            "count": len(transactions),
            "transaction_ids": [t.id for t in transactions],
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_path=request.url.path,
        request_method="POST",
    )
    db.add(audit_log)
    db.commit()

    return JSONResponse(content={
        "message": f"Successfully submitted {len(transactions)} transactions for authorization",
        "count": len(transactions),
        "transaction_ids": [t.id for t in transactions],
    })


@router.post("/authorize/{transaction_id}")
async def authorize_transaction(
    transaction_id: int,
    request_body: AuthorizationRequest,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Authorize or reject a manually reconciled transaction (checker operation).

    Only admins (not super_admins) can authorize/reject transactions.

    Args:
        transaction_id: The transaction ID to authorize/reject.
        request_body: Contains action ('authorize' or 'reject') and optional note.

    Returns:
        Updated transaction details.
    """
    if request_body.action not in ['authorize', 'reject']:
        raise HTTPException(
            status_code=400,
            detail="Action must be 'authorize' or 'reject'"
        )

    # Get the transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate transaction is pending authorization
    if transaction.authorization_status != AuthorizationStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Transaction is not pending authorization"
        )

    # Update transaction based on action
    if request_body.action == 'authorize':
        transaction.authorization_status = AuthorizationStatus.AUTHORIZED.value
        transaction.reconciliation_status = ReconciliationStatus.RECONCILED.value
        message = "Transaction authorized and marked as reconciled"
    else:
        transaction.authorization_status = AuthorizationStatus.REJECTED.value
        transaction.is_manually_reconciled = None
        message = "Transaction authorization rejected"

    transaction.authorized_by = current_user.id
    transaction.authorized_at = datetime.now(ZoneInfo("Africa/Nairobi"))
    transaction.authorization_note = request_body.note

    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action=f"authorization_{request_body.action}",
        resource_type="transaction",
        resource_id=str(transaction_id),
        details={
            "run_id": transaction.run_id,
            "gateway": transaction.gateway,
            "transaction_id": transaction.transaction_id,
            "action": request_body.action,
            "note": request_body.note,
            "manual_recon_by": transaction.manual_recon_by,
            "manual_recon_note": transaction.manual_recon_note,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_path=request.url.path,
        request_method="POST",
    )
    db.add(audit_log)
    db.commit()
    db.refresh(transaction)

    return JSONResponse(content={
        "message": message,
        "transaction": transaction_to_response(transaction),
    })


@router.post("/authorize-bulk")
async def authorize_bulk(
    request_body: dict,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Authorize or reject multiple transactions at once (checker operation).

    Only admins (not super_admins) can authorize/reject transactions.

    Args:
        request_body: {
            "transaction_ids": [1, 2, 3],
            "action": "authorize" or "reject",
            "note": "Optional bulk authorization note"
        }

    Returns:
        Summary of authorized/rejected transactions.
    """
    transaction_ids = request_body.get("transaction_ids", [])
    action = request_body.get("action")
    note = request_body.get("note")

    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")

    if action not in ['authorize', 'reject']:
        raise HTTPException(
            status_code=400,
            detail="Action must be 'authorize' or 'reject'"
        )

    # Get pending transactions
    transactions = db.query(Transaction).filter(
        Transaction.id.in_(transaction_ids),
        Transaction.authorization_status == AuthorizationStatus.PENDING.value
    ).all()

    if not transactions:
        raise HTTPException(
            status_code=404,
            detail="No pending transactions found with the given IDs"
        )

    # Update all transactions
    now = datetime.now(ZoneInfo("Africa/Nairobi"))
    for txn in transactions:
        if action == 'authorize':
            txn.authorization_status = AuthorizationStatus.AUTHORIZED.value
            txn.reconciliation_status = ReconciliationStatus.RECONCILED.value
        else:
            txn.authorization_status = AuthorizationStatus.REJECTED.value
            txn.is_manually_reconciled = None

        txn.authorized_by = current_user.id
        txn.authorized_at = now
        txn.authorization_note = note

    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action=f"bulk_authorization_{action}",
        resource_type="transaction",
        resource_id=f"bulk:{len(transactions)}",
        details={
            "action": action,
            "note": note,
            "count": len(transactions),
            "transaction_ids": [t.id for t in transactions],
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_path=request.url.path,
        request_method="POST",
    )
    db.add(audit_log)
    db.commit()

    return JSONResponse(content={
        "message": f"Successfully {action}d {len(transactions)} transactions",
        "action": action,
        "count": len(transactions),
        "transaction_ids": [t.id for t in transactions],
    })
