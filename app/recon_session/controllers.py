from typing import List
from fastapi import APIRouter, HTTPException, Depends
from .entities import ReconciliationSession
from .services import create_session
from .models import SessionResponse
from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import EntityNotFoundException, NullValueException, ControllerException
from app.database.mysql_configs import Session, get_database


router = APIRouter(prefix='/api/v1', tags=['Reconciliation_sessions'])

@router.post("/session/create")
async def session_create(db: Session=Depends(get_database)):
    response = create_session(db)
    if not response:
        raise ControllerException("Failed to create reconciliation session")
    return {"message": "ReconciliationSession created successfully", "data":response}


@router.get("/session/current")
async def get_current_session():
    session_id = get_current_redis_session_id()
    if not session_id:
        NullValueException("Current session id is null")
    return session_id


@router.get("/session/all", response_model=List[SessionResponse])
async def get_all_sessions(db: Session=Depends(get_database)):
    result = db.query(ReconciliationSession).all()
    if not result:
        raise EntityNotFoundException("Failed to retrieve reconciliation sessions")
    return result




