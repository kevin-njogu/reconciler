import uuid
from typing import List
import pandas as pd
from app.exceptions.exceptions import FileOperationsException


def handle_null_references_column(df: pd.DataFrame, null_cols: List[str], name: str) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        for ref_col in null_cols:
            if ref_col not in dataframe.columns:
                raise  FileOperationsException(f"{ref_col} is missing in the dataframe")
            dataframe[ref_col] = dataframe[ref_col].astype(str).apply(
                lambda x: f"{name}-random_ref-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str)
        return dataframe
    except Exception:
        raise