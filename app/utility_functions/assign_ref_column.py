import pandas as pd

def assign_reference_column(df: pd.DataFrame, ref_column: str, fill_column: str):
    try:
        dataframe = df.copy()
        if ref_column not in df.columns:
            dataframe[ref_column] = dataframe[fill_column]
        return dataframe
    except Exception:
        raise