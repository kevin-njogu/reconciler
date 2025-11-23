from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.database.mysql_configs import get_database
from app.database.redis_configs import get_current_redis_session_id
from app.fileConfigs.EquityConfigs import EquityConfigs
from app.reconciler.Reconciler import GatewayReconciler
from app.fileConfigs.KcbConfigs import KcbConfigs
from app.fileConfigs.MpesaConfigs import MpesaConfigs
from app.fileConfigs.WorkpayConfigs import WorkpayEquityConfigs, WorkpayKcbConfigs, WorkpayMpesaConfigs
from app.reports.download_report import download_gateway_report

router = APIRouter(prefix='/api/v1', tags=['Reconciliation Endpoints'])

db_session = Depends(get_database)

@router.post("/reconcile/{gateway}")
async def reconcile(gateway: str, db: Session=db_session, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id().get("current_session_key")
        session = curr_sess_id if session_id is None else session_id
        if gateway.lower() == "equity":
            reconciler = GatewayReconciler(session_id=session, gateway_configs=EquityConfigs,
                                           workpay_configs=WorkpayEquityConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
        elif gateway.lower() == "kcb":
            reconciler = GatewayReconciler(session_id=session, gateway_configs=KcbConfigs,
                                           workpay_configs=WorkpayKcbConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
        elif gateway.lower() == "mpesa":
            reconciler = GatewayReconciler(session_id=session, gateway_configs=MpesaConfigs,
                                           workpay_configs=WorkpayMpesaConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
        return JSONResponse(content="Reconciliation process completed", status_code=201)
    except Exception:
        raise