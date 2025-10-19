from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.redis_configs import get_current_redis_session_id
from app.gateways.kcb.services import save_reconciled, download_report
from app.database.mysql_configs import Session, get_database

router = APIRouter(prefix='/api/v1', tags=['Kcb_gateway'])



@router.post("/kcb/reconcile")
async def reconcile_kcb(db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        response = save_reconciled(db, session)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/kcb/download")
async def download_kcb(db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        return download_report(db, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))