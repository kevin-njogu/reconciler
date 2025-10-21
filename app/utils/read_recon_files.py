import pandas as pd
from fastapi import HTTPException
from app.utils.constants import *



def read_excel_files(file, sheet_name, engine, skip_rows=0):
    df = pd.read_excel(file, sheet_name=sheet_name, engine=engine, skiprows=skip_rows)
    return df

def get_session():
    session_id = get_current_redis_session_id()
    return session_id
SESSION = get_session()

def get_directory():
    directory = get_uploads_dir(SESSION)
    return directory
UPLOADS_DIR=get_directory()


def read_file( filename_prefix, uploads_dir=UPLOADS_DIR, sheet_name=0, excel_skip_rows=0, csv_skip_rows=0):
    df = pd.DataFrame()
    try:
        if not uploads_dir:
            raise HTTPException(status_code=404, detail='Uploads directory could not be found')

        file_found = False

        for file in uploads_dir.iterdir():
            if not file:
                continue
            if file.name.startswith(filename_prefix):
                file_found = True
                if file.suffix == XLSX_EXTENSION:
                    df = read_excel_files(file, sheet_name=sheet_name, engine=XLSX_ENGINE, skip_rows=excel_skip_rows)
                elif file.suffix == XLS_EXTENSION:
                    df = read_excel_files(file, sheet_name=sheet_name, engine=XLS_ENGINE, skip_rows=excel_skip_rows)
                elif file.suffix == CSV_EXTENSION:
                    df = pd.read_csv(file, skiprows=csv_skip_rows)
                else:
                    raise HTTPException(status_code=400, detail="Read file error: File type not supported")
                break

        if not file_found:
            raise HTTPException(status_code=400, detail="Please upload the necessary files")

        return df
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
