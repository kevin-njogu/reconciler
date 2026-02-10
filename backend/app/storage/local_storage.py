import re
from pathlib import Path
from typing import List, Optional, BinaryIO

from app.exceptions.exceptions import FileUploadException, ReadFileException
from app.storage.base import StorageBackend

# Regex for valid path components (alphanumeric, hyphens, underscores, dots)
_SAFE_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')


def _validate_path_component(name: str, component_type: str = "name") -> None:
    """
    Validate a path component to prevent path traversal attacks.

    Rejects any component containing '..' or '/' or other dangerous patterns.
    """
    if not name:
        raise ValueError(f"Empty {component_type} is not allowed")
    if '..' in name or '/' in name or '\\' in name:
        raise ValueError(f"Invalid {component_type}: path traversal not allowed")
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid {component_type}: only alphanumeric characters, hyphens, underscores, and dots are allowed"
        )


class LocalStorage(StorageBackend):
    """
    Local filesystem storage backend.
    Stores files in: {base_path}/{batch_id}/{gateway}/{filename}
    """

    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path).resolve()

    def _get_batch_path(self, batch_id: str) -> Path:
        """Get the full path for a batch directory."""
        _validate_path_component(batch_id, "batch_id")
        path = (self.base_path / batch_id).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Path traversal detected in batch_id")
        return path

    def _get_file_path(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> Path:
        """Get the full path for a file, optionally within a gateway subdirectory."""
        _validate_path_component(filename, "filename")
        if gateway:
            _validate_path_component(gateway, "gateway")
            path = (self._get_batch_path(batch_id) / gateway / filename).resolve()
        else:
            path = (self._get_batch_path(batch_id) / filename).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Path traversal detected")
        return path

    def save_file(self, batch_id: str, filename: str, content: bytes, gateway: Optional[str] = None) -> str:
        """
        Save a file to local storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to save.
            content: File content as bytes.
            gateway: Optional gateway subdirectory.

        Returns:
            Path where the file was saved.
        """
        try:
            if gateway:
                self.ensure_gateway_directory(batch_id, gateway)
            else:
                self.ensure_batch_directory(batch_id)
            file_path = self._get_file_path(batch_id, filename, gateway)
            with open(file_path, "wb") as f:
                f.write(content)
            return str(file_path)
        except FileUploadException:
            raise
        except OSError as e:
            raise FileUploadException(f"Failed to save file {filename}: {str(e)}")

    def read_file_bytes(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bytes:
        """
        Read a file's content as bytes from local storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to read.
            gateway: Optional gateway subdirectory.

        Returns:
            File content as bytes.
        """
        file_path = self._get_file_path(batch_id, filename, gateway)
        if not file_path.exists():
            raise ReadFileException(f"File not found: {file_path}")
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise ReadFileException(f"Failed to read file {filename}: {str(e)}")

    def list_files(self, batch_id: str, gateway: Optional[str] = None) -> List[str]:
        """
        List all files in a batch directory or gateway subdirectory.

        Args:
            batch_id: The batch identifier.
            gateway: Optional gateway subdirectory name.

        Returns:
            List of filenames.
        """
        if gateway:
            target_path = self._get_batch_path(batch_id) / gateway
        else:
            target_path = self._get_batch_path(batch_id)

        if not target_path.exists():
            if gateway:
                return []  # Gateway dir may not exist yet
            raise ReadFileException(f"Batch directory not found: {batch_id}")
        try:
            return [f.name for f in target_path.iterdir() if f.is_file()]
        except OSError as e:
            raise ReadFileException(f"Failed to list files in {target_path}: {str(e)}")

    def file_exists(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Check if a file exists in local storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to check.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file exists, False otherwise.
        """
        return self._get_file_path(batch_id, filename, gateway).exists()

    def ensure_batch_directory(self, batch_id: str) -> None:
        """
        Ensure the batch directory exists in local storage.

        Args:
            batch_id: The batch identifier.
        """
        try:
            batch_path = self._get_batch_path(batch_id)
            self.base_path.mkdir(parents=True, exist_ok=True)
            batch_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileUploadException(f"Failed to create batch directory {batch_id}: {str(e)}")

    def ensure_gateway_directory(self, batch_id: str, gateway: str) -> None:
        """
        Ensure the gateway subdirectory exists within a batch directory.

        Args:
            batch_id: The batch identifier.
            gateway: The gateway name for the subdirectory.
        """
        try:
            self.ensure_batch_directory(batch_id)
            gateway_path = self._get_batch_path(batch_id) / gateway
            gateway_path.mkdir(parents=True, exist_ok=True)
        except FileUploadException:
            raise
        except OSError as e:
            raise FileUploadException(
                f"Failed to create gateway directory {gateway} in batch {batch_id}: {str(e)}"
            )

    def get_file_handle(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> BinaryIO:
        """
        Get a file handle for reading from local storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file.
            gateway: Optional gateway subdirectory.

        Returns:
            Binary file handle.
        """
        file_path = self._get_file_path(batch_id, filename, gateway)
        if not file_path.exists():
            raise ReadFileException(f"File not found: {file_path}")
        try:
            return open(file_path, "rb")
        except OSError as e:
            raise ReadFileException(f"Failed to open file {filename}: {str(e)}")

    def delete_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Delete a file from local storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to delete.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file was deleted, False if file didn't exist.
        """
        file_path = self._get_file_path(batch_id, filename, gateway)
        if not file_path.exists():
            return False
        try:
            file_path.unlink()
            return True
        except OSError as e:
            raise FileUploadException(f"Failed to delete file {filename}: {str(e)}")

    def delete_batch_directory(self, batch_id: str) -> int:
        """
        Delete all files in a batch directory (including subdirectories) and the directory itself.

        Args:
            batch_id: The batch identifier.

        Returns:
            Number of files deleted.
        """
        batch_path = self._get_batch_path(batch_id)
        if not batch_path.exists():
            return 0
        deleted_count = 0
        try:
            # Recursively delete all files in subdirectories first
            for item in sorted(batch_path.rglob("*"), reverse=True):
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
                elif item.is_dir():
                    item.rmdir()
            batch_path.rmdir()
            return deleted_count
        except OSError as e:
            raise FileUploadException(f"Failed to delete batch directory {batch_id}: {str(e)}")
