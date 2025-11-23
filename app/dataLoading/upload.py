from datetime import datetime
from pathlib import Path
from fastapi import UploadFile
from app.exceptions.exceptions import FileUploadException
from google.cloud import storage
import os

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
storage.Client(project=project_id)


def generate_recon_session_key() -> str:
    try:
        # current_datetime = datetime.now()
        # format_string = "%Y-%m-%d %H:%M:%S"
        # date_string = current_datetime.strftime(format_string).replace(" ", "_")
        # session_key = f"sess:{date_string}"
        session_key = session_id = datetime.now().strftime("sess_%Y-%m-%d_%H-%M-%S")
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

        ####### Upload to local uploads directory #######################
        # current_uploads_dir = get_uploads_dir(session_id)
        # file_path = current_uploads_dir / file.filename
        # try:
        #     with open(file_path, "wb") as buffer:
        #         content = await file.read()
        #         buffer.write(content)
        # except Exception as e:
        #     raise FileUploadException(str(e))
        #################################################################

        ####### Upload to GCS bucket #######################
        file_bytes = await file.read()
        destination_path = f"uploads/{session_id}/{file.filename}"
        result = upload_to_gcs(
            bucket_name="recon_wp",
            destination_path=destination_path,
            file_bytes=file_bytes,
        )
        ###################################################

        return f"{file.filename} uploaded successfully"
    except Exception:
        raise

def upload_to_gcs(bucket_name: str, destination_path: str, file_bytes: bytes):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_path)

        blob.upload_from_string(file_bytes)
        return f"Uploaded to gs://{bucket_name}/{destination_path}"
    except Exception as e:
        raise FileUploadException(str(e))

