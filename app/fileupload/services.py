from pathlib import Path
from fastapi import HTTPException, UploadFile
from app.database.redis import get_current_redis_session_id


async def process_upload_file(file: UploadFile):
    try:
        if file.filename == "":
            raise HTTPException(status_code=400, detail="No file provided")
        if not file.filename.endswith(("xls", "xlsx", "csv")):
            raise HTTPException(status_code=400, detail="Unsupported file type")
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
            raise HTTPException(status_code=400, detail='Bad request, session id and dir_name cannot be null')
        uploads_dir = Path(dir_name)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        session_dir = uploads_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_uploads_dir(session_id):
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        uploads_dir = base_dir / "uploads" / session_id
        return uploads_dir
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


