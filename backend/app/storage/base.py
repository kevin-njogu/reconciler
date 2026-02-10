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
        {base_path}/{gateway}/{filename}
    """

    @abstractmethod
    def save_file(self, gateway: str, filename: str, content: bytes) -> str:
        """
        Save a file to storage.

        Args:
            gateway: The gateway name for directory organization.
            filename: Name of the file to save.
            content: File content as bytes.

        Returns:
            Path or URI where the file was saved.
        """
        pass

    @abstractmethod
    def read_file_bytes(self, gateway: str, filename: str) -> bytes:
        """
        Read a file's content as bytes.

        Args:
            gateway: The gateway directory.
            filename: Name of the file to read.

        Returns:
            File content as bytes.
        """
        pass

    @abstractmethod
    def list_files(self, gateway: str) -> List[str]:
        """
        List all files in a gateway directory.

        Args:
            gateway: The gateway name.

        Returns:
            List of filenames.
        """
        pass

    @abstractmethod
    def file_exists(self, gateway: str, filename: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            gateway: The gateway directory.
            filename: Name of the file to check.

        Returns:
            True if file exists, False otherwise.
        """
        pass

    @abstractmethod
    def ensure_gateway_directory(self, gateway: str) -> None:
        """
        Ensure the gateway directory exists.

        Args:
            gateway: The gateway name for the directory.
        """
        pass

    @abstractmethod
    def get_file_handle(self, gateway: str, filename: str) -> BinaryIO:
        """
        Get a file handle for reading.

        Args:
            gateway: The gateway directory.
            filename: Name of the file.

        Returns:
            Binary file handle.
        """
        pass

    @abstractmethod
    def delete_file(self, gateway: str, filename: str) -> bool:
        """
        Delete a file from storage.

        Args:
            gateway: The gateway directory.
            filename: Name of the file to delete.

        Returns:
            True if file was deleted, False if file didn't exist.
        """
        pass

    def find_file_by_prefix(self, gateway: str, prefix: str) -> Optional[str]:
        """
        Find a file in the gateway directory that starts with the given prefix.

        Args:
            gateway: The gateway directory.
            prefix: The filename prefix to search for.

        Returns:
            Filename if found, None otherwise.
        """
        files = self.list_files(gateway)
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
