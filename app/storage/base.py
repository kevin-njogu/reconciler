from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, BinaryIO

import pandas as pd


# Supported file extensions
XLSX_EXTENSION = ".xlsx"
XLS_EXTENSION = ".xls"
CSV_EXTENSION = ".csv"
SUPPORTED_EXTENSIONS = (XLSX_EXTENSION, XLS_EXTENSION, CSV_EXTENSION)

# Pandas engines for Excel files
XLSX_ENGINE = "openpyxl"
XLS_ENGINE = "xlrd"


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    Provides a common interface for local and cloud storage operations.

    Directory structure:
        {base_path}/{batch_id}/{gateway_name}/{filename}
    """

    @abstractmethod
    def save_file(self, batch_id: str, filename: str, content: bytes, gateway: Optional[str] = None) -> str:
        """
        Save a file to storage.

        Args:
            batch_id: The batch identifier for organizing files.
            filename: Name of the file to save.
            content: File content as bytes.
            gateway: Optional gateway name for subdirectory organization.

        Returns:
            Path or URI where the file was saved.
        """
        pass

    @abstractmethod
    def read_file_bytes(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bytes:
        """
        Read a file's content as bytes.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to read.
            gateway: Optional gateway subdirectory.

        Returns:
            File content as bytes.
        """
        pass

    @abstractmethod
    def list_files(self, batch_id: str, gateway: Optional[str] = None) -> List[str]:
        """
        List all files in a batch directory or gateway subdirectory.

        Args:
            batch_id: The batch identifier.
            gateway: Optional gateway name to list files in subdirectory.

        Returns:
            List of filenames.
        """
        pass

    @abstractmethod
    def file_exists(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Check if a file exists in storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to check.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file exists, False otherwise.
        """
        pass

    @abstractmethod
    def ensure_batch_directory(self, batch_id: str) -> None:
        """
        Ensure the batch directory exists.

        Args:
            batch_id: The batch identifier.
        """
        pass

    @abstractmethod
    def ensure_gateway_directory(self, batch_id: str, gateway: str) -> None:
        """
        Ensure the gateway subdirectory exists within a batch directory.

        Args:
            batch_id: The batch identifier.
            gateway: The gateway name for the subdirectory.
        """
        pass

    @abstractmethod
    def get_file_handle(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> BinaryIO:
        """
        Get a file handle for reading.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file.
            gateway: Optional gateway subdirectory.

        Returns:
            Binary file handle.
        """
        pass

    @abstractmethod
    def delete_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> bool:
        """
        Delete a file from storage.

        Args:
            batch_id: The batch identifier.
            filename: Name of the file to delete.
            gateway: Optional gateway subdirectory.

        Returns:
            True if file was deleted, False if file didn't exist.
        """
        pass

    @abstractmethod
    def delete_batch_directory(self, batch_id: str) -> int:
        """
        Delete all files in a batch directory and the directory itself.

        Args:
            batch_id: The batch identifier.

        Returns:
            Number of files deleted.
        """
        pass

    def batch_directory_exists(self, batch_id: str) -> bool:
        """
        Check if a batch directory exists in storage.

        Args:
            batch_id: The batch identifier.

        Returns:
            True if directory exists, False otherwise.
        """
        try:
            self.list_files(batch_id)
            return True
        except Exception:
            return False

    def find_file_by_prefix(self, batch_id: str, prefix: str, gateway: Optional[str] = None) -> Optional[str]:
        """
        Find a file in the batch/gateway directory that starts with the given prefix.

        Args:
            batch_id: The batch identifier.
            prefix: The filename prefix to search for.
            gateway: Optional gateway subdirectory.

        Returns:
            Filename if found, None otherwise.
        """
        files = self.list_files(batch_id, gateway)
        for filename in files:
            if filename.startswith(prefix):
                return filename
        return None

    def get_file_extension(self, filename: str) -> str:
        """
        Get the file extension from a filename.

        Args:
            filename: The filename.

        Returns:
            File extension (e.g., '.xlsx', '.csv').
        """
        return Path(filename).suffix.lower()

    def is_supported_extension(self, filename: str) -> bool:
        """
        Check if the file has a supported extension.

        Args:
            filename: The filename to check.

        Returns:
            True if supported, False otherwise.
        """
        return filename.lower().endswith(SUPPORTED_EXTENSIONS)
