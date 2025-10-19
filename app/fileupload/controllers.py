from fastapi import APIRouter, File, UploadFile, HTTPException
from .services import process_upload_file

router = APIRouter(prefix="/api/file", tags=["File_upload"])


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="Bad request, please attach a file")
        response = await process_upload_file(file)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"upload file endpoint failed: {str(e)}")



