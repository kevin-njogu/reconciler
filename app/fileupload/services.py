from argparse import FileType
from pathlib import Path
from fastapi import HTTPException, UploadFile
from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import FileTypeException, NullValueException


async def process_upload_file(file: UploadFile):
    try:
        if not file.filename.endswith(("xls", "xlsx", "csv")):
            raise FileTypeException("Failed to upload file: File type not supported")
        curr_session = get_current_redis_session_id()
        curr_session_dir = get_uploads_dir(curr_session)
        filepath = curr_session_dir / file.filename
        await write_file(filepath, file)
        return {"message": f"{file.filename} uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def write_file(filepath, file):
    try:
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        return None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def create_uploads_directory(session_id: str, dir_name: str) -> None:
    try:
        if not (session_id and dir_name):
            raise NullValueException('Failed to create uploads directory: session id or dir name is null')
        uploads_dir = Path(dir_name)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        session_dir = uploads_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_uploads_dir(session_id):
    try:
        if not session_id:
            raise NullValueException("Failed to get uploads directory: session id is null")
        base_dir = Path(__file__).resolve().parent.parent.parent
        uploads_dir = base_dir / "uploads" / session_id
        if not uploads_dir:
            raise NullValueException("Failed to get uploads directory")
        return uploads_dir
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


