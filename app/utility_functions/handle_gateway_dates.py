import pandas as pd


def handle_gateway_date_columns(df: pd.DataFrame, current_date, new_date, date_format: str):
    try:
        dataframe = df.copy()
        dataframe.loc[:, new_date] = df[current_date]
        dataframe[new_date] = (
            dataframe[new_date].astype(str).str.strip().apply(pd.to_datetime, errors='coerce', format=date_format))
        return dataframe
    except Exception:
        raise