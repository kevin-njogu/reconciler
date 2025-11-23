from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.database.redis_configs import *
from app.dataLoading.upload import generate_recon_session_key, create_uploads_directory, process_upload_file

router = APIRouter(prefix='/api/v1', tags=['Session Endpoints'])

db_session = Depends(get_database)

@router.post("/create-session", status_code=201)
async def create_session(db: Session = db_session):
    """
    Create a new reconciliation session.

    - Generates a new session key
    - Creates a corresponding uploads directory
    - Sets the session key in Redis

    Returns:
        JSONResponse: Success message with session key.
    """
    try:
        session_key = generate_recon_session_key()
        #create_uploads_directory(session_key, "uploads") --> Works with local uploads
        message = set_current_redis_session_id(session_key)
        return JSONResponse(content=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")


@router.get("/all/sessions", status_code=200)
async def get_all_sessions():
    """
    Retrieve all existing reconciliation sessions from Redis.

    Returns:
        JSONResponse: List of session keys.
    """
    try:
        keys = get_all_redis_sessions()
        return JSONResponse(content=keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {e}")


@router.get("/current/session", status_code=200)
async def get_current_session():
    """
    Retrieve the current active reconciliation session.

    Returns:
        JSONResponse: Current session key.
    """
    try:
        key = get_current_redis_session_id()
        return JSONResponse(content=key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch current session: {e}")
