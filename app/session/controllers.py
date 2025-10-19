from typing import Annotated, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from .entities import Session
from .services import create_session
from app.database.mysql import get_session
from .session_response import SessionResponse
from ..utils.constants import SESSION

router = APIRouter(prefix='/api/v1', tags=['Create_session'])

SessionDep = Annotated[object, Depends(get_session)]

@router.post("/session/create")
async def session_create(db: SessionDep):
    try:
        response = create_session(db)
        return {"message": "Session created successfully", "data":response}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/session/current")
async def get_current_session():
    try:
        session_id = SESSION
        return session_id
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/session/all", response_model=List[SessionResponse])
async def get_all_sessions(db: SessionDep):
    try:
        stmt = select(Session)
        result = db.execute(stmt).scalars().all()
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))



