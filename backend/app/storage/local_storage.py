import re
from pathlib import Path
from typing import List, BinaryIO

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
    Stores files in: {base_path}/{gateway}/{filename}
    """

    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path).resolve()

    def _get_gateway_path(self, gateway: str) -> Path:
        """Get the full path for a gateway directory."""
        _validate_path_component(gateway, "gateway")
        path = (self.base_path / gateway).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Path traversal detected in gateway")
        return path

    def _get_file_path(self, gateway: str, filename: str) -> Path:
        """Get the full path for a file within a gateway directory."""
        _validate_path_component(filename, "filename")
        path = (self._get_gateway_path(gateway) / filename).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Path traversal detected")
        return path

    def save_file(self, gateway: str, filename: str, content: bytes) -> str:
        """Save a file to local storage."""
        try:
            self.ensure_gateway_directory(gateway)
            file_path = self._get_file_path(gateway, filename)
            with open(file_path, "wb") as f:
                f.write(content)
            return str(file_path)
        except FileUploadException:
            raise
        except OSError as e:
            raise FileUploadException(f"Failed to save file {filename}: {str(e)}")

    def read_file_bytes(self, gateway: str, filename: str) -> bytes:
        """Read a file's content as bytes from local storage."""
        file_path = self._get_file_path(gateway, filename)
        if not file_path.exists():
            raise ReadFileException(f"File not found: {file_path}")
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise ReadFileException(f"Failed to read file {filename}: {str(e)}")

    def list_files(self, gateway: str) -> List[str]:
        """List all files in a gateway directory."""
        target_path = self._get_gateway_path(gateway)

        if not target_path.exists():
            return []
        try:
            return [f.name for f in target_path.iterdir() if f.is_file()]
        except OSError as e:
            raise ReadFileException(f"Failed to list files in {target_path}: {str(e)}")

    def file_exists(self, gateway: str, filename: str) -> bool:
        """Check if a file exists in local storage."""
        return self._get_file_path(gateway, filename).exists()

    def ensure_gateway_directory(self, gateway: str) -> None:
        """Ensure the gateway directory exists in local storage."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            gateway_path = self._get_gateway_path(gateway)
            gateway_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileUploadException(f"Failed to create gateway directory {gateway}: {str(e)}")

    def get_file_handle(self, gateway: str, filename: str) -> BinaryIO:
        """Get a file handle for reading from local storage."""
        file_path = self._get_file_path(gateway, filename)
        if not file_path.exists():
            raise ReadFileException(f"File not found: {file_path}")
        try:
            return open(file_path, "rb")
        except OSError as e:
            raise ReadFileException(f"Failed to open file {filename}: {str(e)}")

    def delete_file(self, gateway: str, filename: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._get_file_path(gateway, filename)
        if not file_path.exists():
            return False
        try:
            file_path.unlink()
            return True
        except OSError as e:
            raise FileUploadException(f"Failed to delete file {filename}: {str(e)}")
