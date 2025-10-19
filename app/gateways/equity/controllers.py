from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.mysql_configs import Session, get_database
from app.database.redis_configs import get_current_redis_session_id
from app.gateways.equity.services import save_reconciled, download_report


router = APIRouter(prefix='/api/v1', tags=['Equity_gateway'])


@router.post("/reconcile/equity")
async def reconcile_equity(db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        response = save_reconciled(db, session)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download/equity")
async def download_equity(db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        return download_report(db, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))