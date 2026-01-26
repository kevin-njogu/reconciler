from typing import Optional, List

from io import BytesIO

import pandas as pd

from app.exceptions.exceptions import ReadFileException
from app.storage.base import (
    StorageBackend,
    XLSX_EXTENSION,
    XLS_EXTENSION,
    CSV_EXTENSION,
    XLSX_ENGINE,
    XLS_ENGINE,
)
from app.storage.config import get_storage
from app.storage.gcs_storage import GcsStorage


def derive_external_gateway(gateway_name: str) -> str:
    """
    Derive the external gateway name (subdirectory) from a gateway name.

    - External gateways (equity, kcb, mpesa) map to themselves.
    - Internal gateways (workpay_equity, workpay_kcb) map to their external counterpart.

    Args:
        gateway_name: The gateway name.

    Returns:
        The external gateway name used as the subdirectory.
    """
    if gateway_name.startswith("workpay_"):
        return gateway_name[len("workpay_"):]
    return gateway_name


class DataLoader:
    """
    Unified data loader that reads files using a pluggable storage backend.
    Supports Excel (.xlsx, .xls) and CSV files.

    Files are organized in gateway subdirectories:
        {batch_id}/{external_gateway}/{gateway_name}.{ext}
    """

    def __init__(self, storage: Optional[StorageBackend] = None):
        """
        Initialize DataLoader with a storage backend.

        Args:
            storage: Storage backend to use. Defaults to environment-configured storage.
        """
        self.storage = storage or get_storage()

    def _read_excel_from_bytes(self, content: bytes, engine: str = XLSX_ENGINE) -> pd.DataFrame:
        """Read Excel file from bytes (first sheet only, no rows skipped)."""
        try:
            return pd.read_excel(BytesIO(content), sheet_name=0, engine=engine)
        except Exception as e:
            raise ReadFileException(f"Error reading Excel content: {str(e)}")

    def _read_excel_from_path(self, file_path: str, engine: str = XLS_ENGINE) -> pd.DataFrame:
        """Read Excel file from path (first sheet only, no rows skipped)."""
        try:
            return pd.read_excel(file_path, sheet_name=0, engine=engine)
        except Exception as e:
            raise ReadFileException(f"Error reading Excel file: {str(e)}")

    def _read_csv_from_bytes(self, content: bytes) -> pd.DataFrame:
        """Read CSV file from bytes (no rows skipped)."""
        try:
            return pd.read_csv(BytesIO(content))
        except Exception as e:
            raise ReadFileException(f"Error reading CSV content: {str(e)}")

    def _read_xlsx_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> pd.DataFrame:
        """Read XLSX file using openpyxl engine."""
        content = self.storage.read_file_bytes(batch_id, filename, gateway=gateway)
        return self._read_excel_from_bytes(content, XLSX_ENGINE)

    def _read_xls_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> pd.DataFrame:
        """Read XLS file. Tries openpyxl first, falls back to xlrd."""
        try:
            content = self.storage.read_file_bytes(batch_id, filename, gateway=gateway)
            return self._read_excel_from_bytes(content, XLSX_ENGINE)
        except Exception:
            pass

        if isinstance(self.storage, GcsStorage):
            temp_path = None
            try:
                temp_path = self.storage.get_file_handle_for_xls(batch_id, filename, gateway=gateway)
                return self._read_excel_from_path(temp_path, XLS_ENGINE)
            finally:
                if temp_path:
                    GcsStorage.cleanup_temp_file(temp_path)
        else:
            content = self.storage.read_file_bytes(batch_id, filename, gateway=gateway)
            return self._read_excel_from_bytes(content, XLS_ENGINE)

    def _read_csv_file(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> pd.DataFrame:
        """Read CSV file."""
        content = self.storage.read_file_bytes(batch_id, filename, gateway=gateway)
        return self._read_csv_from_bytes(content)

    def _read_file_by_extension(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> pd.DataFrame:
        """Read file based on its extension."""
        extension = self.storage.get_file_extension(filename)

        if extension == XLSX_EXTENSION:
            return self._read_xlsx_file(batch_id, filename, gateway=gateway)
        elif extension == XLS_EXTENSION:
            return self._read_xls_file(batch_id, filename, gateway=gateway)
        elif extension == CSV_EXTENSION:
            return self._read_csv_file(batch_id, filename, gateway=gateway)
        else:
            raise ReadFileException(f"Unsupported file type: '{extension}'")

    def find_gateway_files(self, batch_id: str, gateway_name: str) -> List[str]:
        """
        Find files for a specific gateway in its subdirectory.

        With the new directory structure, files are stored as:
            {batch_id}/{external_gateway}/{gateway_name}.{ext}

        Args:
            batch_id: The batch identifier.
            gateway_name: Gateway name to find files for.

        Returns:
            List of matching filenames.
        """
        external_gateway = derive_external_gateway(gateway_name)
        gateway_files = self.storage.list_files(batch_id, gateway=external_gateway)

        # Match files that start with the gateway name
        gateway_lower = gateway_name.lower()
        matching_files = []
        for f in gateway_files:
            f_lower = f.lower()
            name_without_ext = f_lower.rsplit('.', 1)[0] if '.' in f_lower else f_lower
            if name_without_ext == gateway_lower:
                matching_files.append(f)

        return matching_files

    def load_gateway_data(self, batch_id: str, gateway_name: str) -> pd.DataFrame:
        """
        Load data for a specific gateway from a batch.

        Finds the file in the gateway's subdirectory and reads it.

        Args:
            batch_id: The batch identifier.
            gateway_name: Gateway name to load data for (e.g., 'equity', 'workpay_equity').

        Returns:
            DataFrame with file contents.

        Raises:
            ReadFileException: If no file found for the gateway.
        """
        external_gateway = derive_external_gateway(gateway_name)
        gateway_files = self.find_gateway_files(batch_id, gateway_name)

        if not gateway_files:
            raise ReadFileException(
                f"No file found for gateway '{gateway_name}' in batch '{batch_id}'"
            )

        # Read the first matching file from the gateway subdirectory
        filename = gateway_files[0]

        if not self.storage.is_supported_extension(filename):
            extension = self.storage.get_file_extension(filename)
            raise ReadFileException(f"Unsupported file type: '{extension}'")

        return self._read_file_by_extension(batch_id, filename, gateway=external_gateway)

    def load_all_gateway_data(self, batch_id: str, gateway_name: str) -> List[pd.DataFrame]:
        """
        Load data from all files for a specific gateway.

        Args:
            batch_id: The batch identifier.
            gateway_name: Gateway name to load data for.

        Returns:
            List of DataFrames from all matching files.

        Raises:
            ReadFileException: If no files found for the gateway.
        """
        external_gateway = derive_external_gateway(gateway_name)
        gateway_files = self.find_gateway_files(batch_id, gateway_name)

        if not gateway_files:
            raise ReadFileException(
                f"No files found for gateway '{gateway_name}' in batch '{batch_id}'"
            )

        dataframes = []
        for filename in gateway_files:
            if self.storage.is_supported_extension(filename):
                df = self._read_file_by_extension(batch_id, filename, gateway=external_gateway)
                dataframes.append(df)

        if not dataframes:
            raise ReadFileException(
                f"No supported files found for gateway '{gateway_name}' in batch '{batch_id}'"
            )

        return dataframes

    def read_file_by_name(self, batch_id: str, filename: str, gateway: Optional[str] = None) -> pd.DataFrame:
        """
        Read a specific file by exact filename.

        Args:
            batch_id: The batch identifier.
            filename: Exact filename to read.
            gateway: Optional gateway subdirectory.

        Returns:
            DataFrame with file contents.
        """
        if not self.storage.file_exists(batch_id, filename, gateway=gateway):
            raise ReadFileException(f"File not found: '{filename}' in batch '{batch_id}'")

        if not self.storage.is_supported_extension(filename):
            extension = self.storage.get_file_extension(filename)
            raise ReadFileException(f"Unsupported file type: '{extension}'")

        return self._read_file_by_extension(batch_id, filename, gateway=gateway)

    def list_batch_files(self, batch_id: str, gateway: Optional[str] = None) -> List[str]:
        """
        List all files in a batch or gateway subdirectory.

        Args:
            batch_id: The batch identifier.
            gateway: Optional gateway subdirectory to list.

        Returns:
            List of filenames.
        """
        return self.storage.list_files(batch_id, gateway=gateway)
