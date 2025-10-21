from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.mysql_configs import Session, get_database
from app.database.redis_configs import get_current_redis_session_id
from app.gateways.common_services import CommonServices

router = APIRouter(prefix='/api/v1', tags=['Reconciler'])

@router.post("/reconcile/{gateway}")
async def reconcile(gateway: str, db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id()
        session = curr_sess_id if session_id is None else session_id
        service = CommonServices(gateway, db, session)
        response = service.save_reconciled()
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))