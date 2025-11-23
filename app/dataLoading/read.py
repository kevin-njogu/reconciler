from pathlib import Path
from typing import Union, Optional

import pandas as pd

from app.exceptions.exceptions import ReadFileException
from app.dataLoading.upload import get_uploads_dir


class LoadData:
    # Constants
    XLSX_ENGINE = "openpyxl"
    XLS_ENGINE = "xlrd"
    XLSX_EXTENSION = ".xlsx"
    XLS_EXTENSION = ".xls"
    CSV_EXTENSION = ".csv"



    def __init__(self):
        pass



    def __read_excel_file(self, file_path: Union[str, Path], sheet_name: Union[str, int] = 0,
                        engine: Optional[str] = None, skip_rows: int = 0) -> pd.DataFrame:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, skiprows=skip_rows)
            return df
        except Exception as e:
            raise ReadFileException(f"Error reading Excel file {file_path}: {e}")



    def __read_csv_file(self, file_path: Union[str, Path], skip_rows: int = 0) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path, skiprows=skip_rows)
            return df
        except Exception as e:
            raise ReadFileException(f"Error reading CSV file {file_path}: {e}")



    def read_file(self, session_id: str, file_name_prefix: str, sheet_name: Union[str, int] = 0,
                  excel_skip_rows: int = 0, csv_skip_rows: int = 0) -> pd.DataFrame:
        uploads_dir = get_uploads_dir(session_id)
        if not uploads_dir or not uploads_dir.exists():
            raise ReadFileException(f"Uploads directory could not be found for session {session_id}")
        for file in uploads_dir.iterdir():
            if file.name.startswith(file_name_prefix):
                if file.suffix == self.XLSX_EXTENSION:
                    return self.__read_excel_file(file, sheet_name=sheet_name, engine=self.XLSX_ENGINE,
                                                skip_rows=excel_skip_rows)
                elif file.suffix == self.XLS_EXTENSION:
                    try:
                        return self.__read_excel_file(file, sheet_name=sheet_name, engine=self.XLS_ENGINE,
                                                    skip_rows=excel_skip_rows)
                    except Exception:
                        return self.__read_excel_file(file, sheet_name=sheet_name, engine=self.XLSX_ENGINE,
                                                    skip_rows=excel_skip_rows)
                elif file.suffix == self.CSV_EXTENSION:
                    return self.__read_csv_file(file, skip_rows=csv_skip_rows)
                else:
                    raise ReadFileException(f"File type not supported: '{file.suffix}'")

        # If no matching file is found
        raise ReadFileException(f"No file found with name '{file_name_prefix}' in '{uploads_dir}'")