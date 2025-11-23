import os

import pandas as pd
import gcsfs
from urllib.parse import unquote
from typing import Union
import tempfile

from app.exceptions.exceptions import ReadFileException


class LoadDataFromGcs:
    XLSX_ENGINE = "openpyxl"
    XLS_ENGINE = "xlrd"
    XLSX_EXTENSION = ".xlsx"
    XLS_EXTENSION = ".xls"
    CSV_EXTENSION = ".csv"

    def __init__(self, gcs_bucket: str):
        """
        :param gcs_bucket: Name of your GCS bucket (e.g., "recon_wp")
        """
        self.gcs_bucket = gcs_bucket
        self.fs = gcsfs.GCSFileSystem()  # Uses ADC (Application Default Credentials)

    # ---------------------
    # Private read methods
    # ---------------------
    def __read_excel_file_gcs(self, gcs_uri: str, sheet_name=0, engine=None, skip_rows=0):
        try:
            with self.fs.open(gcs_uri, "rb") as f:
                return pd.read_excel(f, sheet_name=sheet_name, engine=engine, skiprows=skip_rows)
        except Exception as e:
            raise ReadFileException(f"Error reading Excel file {gcs_uri}: {e}")

    def __read_xls_file_gcs(self, gcs_path: str, sheet_name=0, skip_rows=0):
        """
        XLS files need a real file on disk because xlrd cannot read streams
        """
        try:
            # gcs_path should be something fs.open() can read directly
            with self.fs.open(gcs_path, "rb") as f:
                content = f.read()
                if not content:
                    raise ReadFileException(f"File is empty: {gcs_path}")

                # Write to a temp file
                with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp_file:
                    tmp_file.write(content)
                    tmp_file.flush()
                    tmp_path = tmp_file.name

                # Read Excel
                df = pd.read_excel(tmp_path, sheet_name=sheet_name, engine=self.XLS_ENGINE, skiprows=skip_rows)
                os.remove(tmp_path)
                return df
        except Exception as e:
            raise ReadFileException(f"Error reading XLS file {gcs_path}: {e}")


    def __read_csv_file_gcs(self, gcs_uri: str, skip_rows=0):
        try:
            with self.fs.open(gcs_uri, "rb") as f:
                return pd.read_csv(f, skiprows=skip_rows)
        except Exception as e:
            raise ReadFileException(f"Error reading CSV file {gcs_uri}: {e}")

    # ---------------------
    # Public method
    # ---------------------
    def read_file(
        self,
        session_id: str,
        file_name_prefix: str,
        sheet_name: Union[str, int] = 0,
        excel_skip_rows: int = 0,
        csv_skip_rows: int = 0
    ) -> pd.DataFrame:
        """
        Read a file from GCS session folder matching the given prefix.
        Supports XLSX, XLS, CSV.
        """
        gcs_folder = f"{self.gcs_bucket}/uploads/{session_id}/"

        # List all objects in the session folder
        try:
            files = self.fs.ls(gcs_folder)
        except FileNotFoundError:
            raise ReadFileException(f"No folder found for session '{session_id}' in bucket '{self.gcs_bucket}'")

        for file in files:
            decoded_path = unquote(file)
            filename = decoded_path.split("/")[-1]

            if filename.startswith(file_name_prefix):
                if filename.endswith(self.XLSX_EXTENSION):
                    return self.__read_excel_file_gcs(decoded_path, sheet_name, self.XLSX_ENGINE, excel_skip_rows)

                if filename.endswith(self.XLS_EXTENSION):
                    # Try openpyxl first
                    try:
                        return self.__read_excel_file_gcs(decoded_path, sheet_name, self.XLSX_ENGINE, excel_skip_rows)
                    except Exception:
                        # Fall back to xlrd if truly .xls
                        return self.__read_xls_file_gcs(decoded_path, sheet_name, skip_rows=excel_skip_rows)

                if filename.endswith(self.CSV_EXTENSION):
                    return self.__read_csv_file_gcs(decoded_path, skip_rows=csv_skip_rows)

                raise ReadFileException(f"Unsupported file type: {filename}")

        # No matching file found
        raise ReadFileException(f"No file with prefix '{file_name_prefix}' found in '{gcs_folder}'")
