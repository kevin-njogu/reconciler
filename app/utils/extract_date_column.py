from typing import List
import pandas as pd
from fastapi import HTTPException


def extract_date_column(df: pd.DataFrame, possible_date_cols: List[str], date_format="%d-%m-%Y"):

    try:
        for date_col in possible_date_cols:
            if date_col in df.columns:
                date = pd.to_datetime(df[date_col], format=date_format, errors="coerce")
                return date
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))