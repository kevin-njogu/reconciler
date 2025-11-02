import pandas as pd

def drop_bottom_rows(df: pd.DataFrame) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        empty_rows = dataframe.isnull().all(axis=1)
        first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(dataframe)
        if empty_rows.any():
            return dataframe.loc[:first_empty_idx - 1]
        else:
            return dataframe
    except Exception:
        raise