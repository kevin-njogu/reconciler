import shutil

from fastapi import HTTPException
from pathlib import Path

def clean_up_uploads():
    UPLOAD_DIR = Path(__file__).parent / "uploads"

    try:
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
            return "Upload directory removed"
        else:
            return "Upload directory does not exist"
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error cleaning up upload files")