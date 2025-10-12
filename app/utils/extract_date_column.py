import pandas as pd

def extract_date_column(df, possible_cols, date_format="%d-%m-%Y"):
    for col in possible_cols:
        if col in df.columns:
            return pd.to_datetime(df[col], format=date_format, errors="coerce")
    raise KeyError(f"None of these date columns were found: {possible_cols}")