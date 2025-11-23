from datetime import datetime
from pathlib import Path
from fastapi import UploadFile
from app.exceptions.exceptions import FileUploadException


def generate_recon_session_key() -> str:
    try:
        current_datetime = datetime.now()
        format_string = "%Y-%m-%d %H:%M:%S"
        date_string = current_datetime.strftime(format_string).replace(" ", "_")
        session_key = f"sess:{date_string}"
        if not session_key:
            raise FileUploadException("Failed to generate  recon session key")
        return session_key
    except Exception:
        raise


def create_uploads_directory(session_id: str, dir_name: str) -> None:
    try:
        uploads_dir = Path(dir_name)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        session_dir = uploads_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return None
    except Exception:
        raise


def get_uploads_dir(session_id: str) -> Path:
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        uploads_dir = base_dir / "uploads" / session_id

        if not uploads_dir.exists():
            raise FileUploadException(f"Uploads directory not found: {uploads_dir}")

        return uploads_dir
    except Exception:
        raise


async def process_upload_file(file: UploadFile, session_id: str) -> str:
    try:
        if not file:
            raise FileUploadException("File must be attached")

        if not file.filename.endswith(("xls", "xlsx", "csv")):
            raise FileUploadException("Unsupported file format")

        current_uploads_dir = get_uploads_dir(session_id)

        file_path = current_uploads_dir / file.filename

        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            raise FileUploadException(str(e))

        return f"{file.filename} uploaded successfully"
    except Exception:
        raise



