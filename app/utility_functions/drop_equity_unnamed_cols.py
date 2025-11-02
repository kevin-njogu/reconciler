from typing import List
import pandas as pd


def drop_unnamed_columns(df: pd.DataFrame, columns: List[str]):
    try:
        dataframe = df.copy()
        exists_unnamed_cols = any(col in columns for col in df.columns)
        new_dataframe = dataframe.drop(columns=columns) if exists_unnamed_cols else dataframe
        return new_dataframe
    except Exception:
        raise