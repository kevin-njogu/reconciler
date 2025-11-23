from fastapi import APIRouter, UploadFile, Depends, File
from starlette.responses import JSONResponse

from app.dataLoading.upload import process_upload_file
from app.database.redis_configs import get_current_redis_session_id

router = APIRouter(prefix='/api/v1', tags=['File Upload Endpoints'])

@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...), session_id: dict = Depends(get_current_redis_session_id)):
    try:
        session_key = session_id.get("current_session_key")
        response = await process_upload_file(file, session_key)
        return JSONResponse(content=response, status_code=201)
    except Exception:
        raise