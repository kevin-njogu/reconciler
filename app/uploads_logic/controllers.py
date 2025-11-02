from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.database.redis_configs import *
from app.uploads_logic.handle_uploads import generate_recon_session_key, create_uploads_directory, process_upload_file

router = APIRouter(prefix='/api/v1', tags=['Handle Uploads'])

db_session = Depends(get_database)

@router.post("/create-session")
async def create_session(db: Session=db_session):
    try:
        session_key = generate_recon_session_key()
        create_uploads_directory(session_key, "uploads")
        message= set_current_redis_session_id(session_key)
        return JSONResponse(content=message, status_code=201)
    except Exception:
        raise


@router.get("/all/sessions")
async def get_all_sessions():
    try:
        keys = get_all_redis_sessions()
        return JSONResponse(content=keys, status_code=200)
    except Exception:
        raise


@router.get("/current/session")
async def get_current_session():
    try:
        key = get_current_redis_session_id()
        return JSONResponse(content=key, status_code=200)
    except Exception:
        raise


@router.post("/upload/file", description="equity, wp-equity, utility, mmf, wp-mpesa, kcb, wp-kcb")
async def upload_file(file: UploadFile = File(...), session_id: dict = Depends(get_current_redis_session_id)):
    try:
        session_key = session_id.get("current_session_key")
        response = await process_upload_file(file, session_key)
        return JSONResponse(content=response, status_code=201)
    except Exception:
        raise
