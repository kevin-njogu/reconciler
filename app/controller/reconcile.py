from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.database.mysql_configs import get_database
from app.database.redis_configs import get_current_redis_session_id
from app.fileConfigs.EquityConfigs import EquityConfigs
from app.reconciler.Reconciler import GatewayReconciler
from app.fileConfigs.KcbConfigs import KcbConfigs
from app.fileConfigs.MpesaConfigs import MpesaConfigs
from app.fileConfigs.WorkpayConfigs import WorkpayEquityConfigs, WorkpayKcbConfigs, WorkpayMpesaConfigs

router = APIRouter(prefix='/api/v1', tags=['Reconciliation Endpoints'])

db_session = Depends(get_database)

# Mapping of gateway names to their configuration classes
GATEWAY_CONFIGS = {
    "equity": (EquityConfigs, WorkpayEquityConfigs),
    "kcb": (KcbConfigs, WorkpayKcbConfigs),
    "mpesa": (MpesaConfigs, WorkpayMpesaConfigs),
}

@router.post("/reconcile/{gateway}")
async def reconcile(
    gateway: str,
    db: Session = db_session,
    session_id: Optional[str] = Query(default=None)
):
    """
    Reconcile transactions for the specified payment gateway.

    This endpoint initiates the reconciliation process for a given gateway.
    It selects the appropriate configuration classes based on the gateway,
    initializes the `GatewayReconciler`, and saves the reconciliation results.

    Args:
        gateway (str): Name of the gateway to reconcile (e.g., "equity", "kcb", "mpesa").
        db (Session, optional): SQLAlchemy database session.
        session_id (str, optional): Specific reconciliation session ID.
            If not provided, the current session ID from Redis is used.

    Returns:
        JSONResponse: A success message with HTTP status code 201.

    Raises:
        HTTPException
            - 400 if the provided gateway is unsupported.
            - 500 for any errors during the reconciliation process.
    """
    try:
        # Determine current session
        curr_sess_id = get_current_redis_session_id().get("current_session_key")
        session = session_id or curr_sess_id

        gateway_lower = gateway.lower()
        if gateway_lower not in GATEWAY_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unsupported gateway '{gateway}'")

        gateway_conf, workpay_conf = GATEWAY_CONFIGS[gateway_lower]

        reconciler = GatewayReconciler(
            session_id=session,
            gateway_configs=gateway_conf,
            workpay_configs=workpay_conf,
            gateway_name=gateway_lower,
            db_session=db
        )
        reconciler.save_reconciled()

        return JSONResponse(content="Reconciliation process completed", status_code=201)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error reconciling {gateway} gateway: {e}")
