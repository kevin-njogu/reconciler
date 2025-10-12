import pandas as pd

def convert_to_numeric(df: pd.DataFrame, columns: list[str]):
    df_copy = df.copy()
    df_copy.loc[:, columns] = (
        df_copy[columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )
    return df_copy