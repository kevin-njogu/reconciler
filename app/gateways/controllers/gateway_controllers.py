from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.database.mysql_configs import get_database
from app.database.redis_configs import get_current_redis_session_id
from app.gateways.equity.EquityConfigs import EquityConfigs
from app.gateways.equity.EquityGatewayReconciler import EquityGatewayReconciler
from app.gateways.equity.KcbConfigs import KcbConfigs
from app.gateways.equity.MpesaConfigs import MpesaConfigs
from app.gateways.equity.WorkpayConfigs import WorkpayEquityConfigs, WorkpayKcbConfigs, WorkpayMpesaConfigs
from app.gateways.equity.reconcile_equity import save_reconciled as equity_reconciler
from app.gateways.kcb.reconcile_kcb import save_reconciled as kcb_reconciler
from app.gateways.mpesa.reconcile_mpesa import save_reconciled as mpesa_reconciler
from app.gateways.services.download_report import download_gateway_report

router = APIRouter(prefix='/api/v1', tags=['Gateway Controller'])



db_session = Depends(get_database)

@router.get("/reconcile/{gateway}")
async def reconcile(gateway: str, db: Session=db_session, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id().get("current_session_key")
        print(curr_sess_id)
        session = curr_sess_id if session_id is None else session_id
        if gateway.lower() == "equity":
            reconciler = EquityGatewayReconciler(session_id=session, gateway_configs=EquityConfigs,
                                                 workpay_configs=WorkpayEquityConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
            # equity_reconciler(db, session)
        elif gateway.lower() == "kcb":
            reconciler = EquityGatewayReconciler(session_id=session, gateway_configs=KcbConfigs,
                                                 workpay_configs=WorkpayKcbConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
            # kcb_reconciler(db, session)
        elif gateway.lower() == "mpesa":
            reconciler = EquityGatewayReconciler(session_id=session, gateway_configs=MpesaConfigs,
                                                 workpay_configs=WorkpayMpesaConfigs, gateway_name=gateway, db_session= db)
            reconciler.save_reconciled()
            # mpesa_reconciler(db, session)
        return JSONResponse(content="Reconciliation process completed", status_code=201)
    except Exception:
        raise


@router.get("/download/{gateway}")
async def download_report(gateway: str, db: Session=db_session, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id().get("current_session_key")
        session = curr_sess_id if session_id is None else session_id
        response = download_gateway_report(db, gateway, session)
        return response
    except Exception:
        raise