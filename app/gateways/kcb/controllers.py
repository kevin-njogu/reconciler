from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.mysql import get_session
from app.database.redis import get_current_redis_session_id
from app.gateways.kcb.services import save_reconciled, download_report

router = APIRouter(prefix='/api/v1', tags=['Kcb_gateway'])

SessionDep = Annotated[object, Depends(get_session)]

@router.post("/kcb/reconcile")
async def reconcile_kcb(db: SessionDep, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        response = save_reconciled(db, session)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/kcb/download")
async def download_kcb(db: SessionDep, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        return download_report(db, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))