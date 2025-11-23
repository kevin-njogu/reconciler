from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.mysql_configs import get_database
from app.database.redis_configs import get_current_redis_session_id
from app.reports.download_report import download_gateway_report

router = APIRouter(prefix='/api/v1', tags=['Report Endpoints'])

db_session = Depends(get_database)


@router.post("/download/{gateway}")
async def download_report(gateway: str, db: Session=db_session, session_id: Optional[str] = Query(default=None)):
    try:
        curr_sess_id = get_current_redis_session_id().get("current_session_key")
        session = curr_sess_id if session_id is None else session_id
        response = download_gateway_report(db, gateway, session)
        return response
    except Exception:
        raise