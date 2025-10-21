from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.mysql_configs import Session, get_database
from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import ServiceExecutionException
from app.gateways.common_services import CommonServices

# router = APIRouter(prefix='/api/v1', tags=['Equity_gateway'])



# @router.get("/download/equity")
# async def download_equity(db: Session=Depends(get_database), session_id: Optional[str] = Query(default=None)):
#     try:
#         curr_sess_id = get_current_redis_session_id()
#         session = curr_sess_id if session_id is None else session_id
#         return download_report(db, session)
#     except Exception as e:
#         raise HTTPException(status_code=404, detail=str(e))