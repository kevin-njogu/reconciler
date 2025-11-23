import pandas as pd
from app.exceptions.exceptions import ReadFileException
from app.dataLoading.upload import get_uploads_dir

XLSX_ENGINE = "openpyxl"
XLS_ENGINE = "xlrd"
XLSX_EXTENSION = ".xlsx"
XLS_EXTENSION = ".xls"
CSV_EXTENSION = ".csv"

def read_excel_files(file, sheet_name, engine, skip_rows=0):
    df = pd.read_excel(file, sheet_name=sheet_name, engine=engine, skiprows=skip_rows)
    return df


def read_file(session_id:str, filename_prefix, sheet_name=0, excel_skip_rows=0, csv_skip_rows=0):
    try:
        uploads_dir = get_uploads_dir(session_id)

        if not uploads_dir:
            raise ReadFileException(f"Uploads directory could not be found ")

        df = pd.DataFrame()
        for file in uploads_dir.iterdir():
            if file.name.startswith(filename_prefix):
                if file.suffix == XLSX_EXTENSION:
                    df = read_excel_files(file, sheet_name=sheet_name, engine=XLSX_ENGINE, skip_rows=excel_skip_rows)
                elif file.suffix == XLS_EXTENSION:
                    #df = read_excel_files(file, sheet_name=sheet_name, engine=XLS_ENGINE, skip_rows=excel_skip_rows)
                    try:
                        df = read_excel_files(file, sheet_name=sheet_name, engine=XLS_ENGINE, skip_rows=excel_skip_rows)
                    except Exception:
                        # fallback if .xls file is actually .xlsx
                        df = read_excel_files(file, sheet_name=sheet_name, engine=XLSX_ENGINE, skip_rows=excel_skip_rows)
                elif file.suffix == CSV_EXTENSION:
                    df = pd.read_csv(file, skiprows=csv_skip_rows)
                else:
                    raise ReadFileException(f"Read file error: File type not supported")
                break
        return df
    except FileNotFoundError as e:
        raise ReadFileException(f"File not found {str(e)}")
    except Exception:
        raise
