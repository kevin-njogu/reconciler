from typing import List
import pandas as pd


def handle_numeric_columns(df: pd.DataFrame, columns: List[str]):
    try:
        dataframe = df.copy()
        def clean_numeric(col):
            col = col.astype(str).str.strip().str.replace("'", "", regex=False)
            col = col.str.replace(",", "", regex=False)
            return pd.to_numeric(col, errors='coerce').fillna(0).abs()
        dataframe.loc[:, columns] = dataframe[columns].apply(clean_numeric)
        return dataframe
    except Exception:
        raise