from fastapi import APIRouter, File, UploadFile, HTTPException
from .services import process_upload_file
from ..exceptions.exceptions import NullValueException

router = APIRouter(prefix="/api/file", tags=["File_upload"])


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file:
            raise FileNotFoundError("File attachment not found")
        response = await process_upload_file(file)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



