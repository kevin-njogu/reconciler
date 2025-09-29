from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path

router = APIRouter(
    prefix="/api/file",
    tags=["file"],
    responses={404: {"description": "Failed to upload file"}}
)

@router.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    try:
        if file.filename == "":
            raise HTTPException(status_code=400, detail="No filename provided")
        if not file.filename.endswith(("xls", "xlsx", "csv")):
            raise HTTPException(status_code=400, detail="Unsupported file type")

        UPLOAD_DIR = Path(__file__).parent / "uploads"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filepath = UPLOAD_DIR / file.filename

        try:
            with open(filepath, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"File could not be uploaded: {str(e)}")

        # return clean_up_uploads()
        return {"filename": file.filename, "content_type": file.content_type}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"upload file endpoint failed: {str(e)}")



