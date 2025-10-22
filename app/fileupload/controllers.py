from fastapi import APIRouter, File, UploadFile, HTTPException
from .services import process_upload_file


router = APIRouter(prefix="/api/file", tags=["File_upload"])


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file attached.")
    try:
        response = await process_upload_file(file)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error {str(e)}")



