import pandas as pd
from app.exceptions.exceptions import FileOperationsException


def handle_workpay_files_dates(df: pd.DataFrame, date_col: str, date_format: str) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        if date_col not in dataframe.columns:
            raise FileOperationsException(f"{date_col} is missing in your workpay file")
        dataframe.loc[:, date_col] = (dataframe[date_col].apply(pd.to_datetime, errors="coerce", format=date_format))
        return dataframe
    except Exception:
        raise