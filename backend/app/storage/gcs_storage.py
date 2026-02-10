import os
import tempfile
from typing import List, Optional, BinaryIO
from urllib.parse import unquote

import gcsfs

from app.exceptions.exceptions import FileUploadException, ReadFileException
from app.storage.base import StorageBackend, XLS_EXTENSION


class GcsStorage(StorageBackend):
    """
    Google Cloud Storage backend.
    Stores files in: gs://{bucket}/{batch_id}/{gateway}/{filename}
    """

    def __init__(self, bucket: str):
        """
        Initialize GCS storage backend.

        Args:
            bucket: Name of the GCS bucket.
        """
        self.bucket = bucket
        self.fs = gcsfs.GCSFileSystem()

    def _get_gcs_path(self, batch_id: str, filename: str = "", gateway: Optional[str] = None) -> str:
        """Get the full GCS path for a file or directory."""
        if gateway and filename:
            return f"{self.bucket}/{batch_id}/{gateway}/{filename}"
        if gateway:
            return f"{self.bucket}/{batch_id}/{gateway}"
        if filename:
            return f"{self.bucket}/{batch_id}/{filename}"
        return f"{self.bucket}/{batch_id}"

    def save_file(self, batch_id: str, filename: str, content: bytes, gateway: Optional[str] = None) -> str:
        """
        Save a file to GCS.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to save.
            content: File content as bytes.
            gateway: Optional gateway subdirectory.

        Returns:
            GCS URI where the file was saved.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, filename, gateway)
            with self.fs.open(gcs_path, "wb") as f:
                f.write(content)
            return f"gs://{gcs_path}"
        except Exception as e:
            raise FileUploadException(f"Failed to save file to GCS {filename}: {str(e)}")

    def read_file_bytes(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bytes:
        """
        Read a file's content as bytes from GCS.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to read.
            gateway: Optional gateway subdirectory.

        Returns:
            File content as bytes.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, filename, gateway)
            with self.fs.open(gcs_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise ReadFileException(f"File not found in GCS: {filename}")
        except Exception as e:
            raise ReadFileException(f"Failed to read file from GCS {filename}: {str(e)}")

    def list_files(self, batch_id: str, gateway: Optional[str] = None) -> List[str]:
        """
        List all files in a batch directory or gateway subdirectory in GCS.

        Args:
            batch_id: The batch identifier.
            gateway: Optional gateway subdirectory name.

        Returns:
            List of filenames.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, gateway=gateway)
            if not self.fs.exists(gcs_path):
                if gateway:
                    return []
                raise ReadFileException(f"Batch directory not found in GCS: {batch_id}")
            files = self.fs.ls(gcs_path)
            # Extract just the filename from full path and decode URL encoding
            # Filter out subdirectories (they won't have file extensions)
            result = []
            for f in files:
                name = unquote(f.split("/")[-1])
                if name and self.is_supported_extension(name):
                    result.append(name)
            return result
        except ReadFileException:
            raise
        except FileNotFoundError:
            if gateway:
                return []
            raise ReadFileException(f"Batch directory not found in GCS: {batch_id}")
        except Exception as e:
            raise ReadFileException(f"Failed to list files in GCS: {str(e)}")

    def file_exists(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Check if a file exists in GCS.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to check.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file exists, False otherwise.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, filename, gateway)
            return self.fs.exists(gcs_path)
        except Exception:
            return False

    def ensure_batch_directory(self, batch_id: str) -> None:
        """
        Ensure the batch directory exists in GCS.
        GCS directories are virtual - no action needed.

        Args:
            batch_id: The batch identifier.
        """
        pass

    def ensure_gateway_directory(self, batch_id: str, gateway: str) -> None:
        """
        Ensure the gateway subdirectory exists in GCS.
        GCS directories are virtual - no action needed.

        Args:
            batch_id: The batch identifier.
            gateway: The gateway name for the subdirectory.
        """
        pass

    def get_file_handle(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> BinaryIO:
        """
        Get a file handle for reading from GCS.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file.
            gateway: Optional gateway subdirectory.

        Returns:
            Binary file handle.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, filename, gateway)
            return self.fs.open(gcs_path, "rb")
        except FileNotFoundError:
            raise ReadFileException(f"File not found in GCS: {filename}")
        except Exception as e:
            raise ReadFileException(f"Failed to open file from GCS {filename}: {str(e)}")

    def get_file_handle_for_xls(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> str:
        """
        Get a local temp file path for XLS files.
        xlrd requires a real file on disk, not a stream.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file.
            gateway: Optional gateway subdirectory.

        Returns:
            Path to temporary file.
        """
        try:
            content = self.read_file_bytes(batch_id, filename, gateway)
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
        """
        Clean up a temporary file created for XLS reading.

        Args:
            temp_path: Path to the temporary file.
        """
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass  # Ignore cleanup errors

    def delete_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Delete a file from GCS.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to delete.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file was deleted, False if file didn't exist.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id, filename, gateway)
            if not self.fs.exists(gcs_path):
                return False
            self.fs.rm(gcs_path)
            return True
        except Exception as e:
            raise FileUploadException(f"Failed to delete file from GCS {filename}: {str(e)}")

    def delete_batch_directory(self, batch_id: str) -> int:
        """
        Delete all files in a batch directory in GCS (including subdirectories).

        Args:
            batch_id: The batch identifier.

        Returns:
            Number of files deleted.
        """
        try:
            gcs_path = self._get_gcs_path(batch_id)
            if not self.fs.exists(gcs_path):
                return 0
            files = self.fs.find(gcs_path)
            deleted_count = len(files)
            if deleted_count > 0:
                self.fs.rm(gcs_path, recursive=True)
            return deleted_count
        except Exception as e:
            raise FileUploadException(f"Failed to delete batch directory from GCS {batch_id}: {str(e)}")
