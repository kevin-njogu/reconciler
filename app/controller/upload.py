from fastapi import APIRouter, UploadFile, Depends, File, HTTPException
from starlette.responses import JSONResponse

from app.dataLoading.upload import process_upload_file
from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import FileUploadException

router = APIRouter(prefix='/api/v1', tags=['File Upload Endpoints'])

# @router.post("/upload/file")
# async def upload_file(file: UploadFile = File(...), session_id: dict = Depends(get_current_redis_session_id)):
#     try:
#         session_key = session_id.get("current_session_key")
#         response = await process_upload_file(file, session_key)
#         return JSONResponse(content=response, status_code=201)
#     except Exception:
#         raise

@router.post("/upload/file", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    session_data: dict = Depends(get_current_redis_session_id)
):
    """
    Upload a file for the current reconciliation session.

    Args:
        file (UploadFile): The file to upload.
        session_data (dict): Injected via dependency, contains current session key.

    Returns:
        JSONResponse: Success message if the file is uploaded successfully.

    Raises:
        HTTPException: If the upload fails or session key is missing.
    """
    session_key = session_data.get("current_session_key")
    if not session_key:
        raise HTTPException(status_code=400, detail="No active session found.")

    try:
        response = await process_upload_file(file, session_key)
        return JSONResponse(content=response)
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")