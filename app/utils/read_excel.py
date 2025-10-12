import pandas as pd

def read_excel_files(file, sheet_name, engine, skip_rows=0):
    df = pd.read_excel(file, sheet_name=sheet_name, engine=engine, skiprows=skip_rows)
    return df