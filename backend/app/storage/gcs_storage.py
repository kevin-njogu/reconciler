import os
import tempfile
from typing import List, BinaryIO
from urllib.parse import unquote

import gcsfs

from app.exceptions.exceptions import FileUploadException, ReadFileException
from app.storage.base import StorageBackend, XLS_EXTENSION


class GcsStorage(StorageBackend):
    """
    Google Cloud Storage backend.
    Stores files in: gs://{bucket}/{gateway}/{filename}
    """

    def __init__(self, bucket: str):
        self.bucket = bucket
        self.fs = gcsfs.GCSFileSystem()

    def _get_gcs_path(self, gateway: str, filename: str = "") -> str:
        """Get the full GCS path for a file or directory."""
        if filename:
            return f"{self.bucket}/{gateway}/{filename}"
        return f"{self.bucket}/{gateway}"

    def save_file(self, gateway: str, filename: str, content: bytes) -> str:
        """Save a file to GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway, filename)
            with self.fs.open(gcs_path, "wb") as f:
                f.write(content)
            return f"gs://{gcs_path}"
        except Exception as e:
            raise FileUploadException(f"Failed to save file to GCS {filename}: {str(e)}")

    def read_file_bytes(self, gateway: str, filename: str) -> bytes:
        """Read a file's content as bytes from GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway, filename)
            with self.fs.open(gcs_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise ReadFileException(f"File not found in GCS: {filename}")
        except Exception as e:
            raise ReadFileException(f"Failed to read file from GCS {filename}: {str(e)}")

    def list_files(self, gateway: str) -> List[str]:
        """List all files in a gateway directory in GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway)
            if not self.fs.exists(gcs_path):
                return []
            files = self.fs.ls(gcs_path)
            result = []
            for f in files:
                name = unquote(f.split("/")[-1])
                if name and self.is_supported_extension(name):
                    result.append(name)
            return result
        except FileNotFoundError:
            return []
        except Exception as e:
            raise ReadFileException(f"Failed to list files in GCS: {str(e)}")

    def file_exists(self, gateway: str, filename: str) -> bool:
        """Check if a file exists in GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway, filename)
            return self.fs.exists(gcs_path)
        except Exception:
            return False

    def ensure_gateway_directory(self, gateway: str) -> None:
        """GCS directories are virtual - no action needed."""
        pass

    def get_file_handle(self, gateway: str, filename: str) -> BinaryIO:
        """Get a file handle for reading from GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway, filename)
            return self.fs.open(gcs_path, "rb")
        except FileNotFoundError:
            raise ReadFileException(f"File not found in GCS: {filename}")
        except Exception as e:
            raise ReadFileException(f"Failed to open file from GCS {filename}: {str(e)}")

    def get_file_handle_for_xls(self, gateway: str, filename: str) -> str:
        """
        Get a local temp file path for XLS files.
        xlrd requires a real file on disk, not a stream.
        """
        try:
            content = self.read_file_bytes(gateway, filename)
            if not content:
                raise ReadFileException(f"File is empty: {filename}")

            with tempfile.NamedTemporaryFile(suffix=XLS_EXTENSION, delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                return tmp_file.name
        except ReadFileException:
            raise
        except Exception as e:
            raise ReadFileException(f"Failed to create temp file for XLS {filename}: {str(e)}")

    @staticmethod
    def cleanup_temp_file(temp_path: str) -> None:
        """Clean up a temporary file created for XLS reading."""
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass

    def delete_file(self, gateway: str, filename: str) -> bool:
        """Delete a file from GCS."""
        try:
            gcs_path = self._get_gcs_path(gateway, filename)
            if not self.fs.exists(gcs_path):
                return False
            self.fs.rm(gcs_path)
            return True
        except Exception as e:
            raise FileUploadException(f"Failed to delete file from GCS {filename}: {str(e)}")
