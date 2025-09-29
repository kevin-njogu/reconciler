from pathlib import Path
from fastapi import HTTPException

def get_upload_dir():
    try:
        current_file = Path(__file__).parent
        current_dir = current_file.parent
        file_upload_dir = current_dir / "fileupload"
        upload_dir = file_upload_dir / "uploads"
        return upload_dir
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch upload dir path: {str(e)}")