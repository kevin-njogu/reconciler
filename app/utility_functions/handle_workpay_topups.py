import pandas as pd

from app.utility_functions.constant_variables import TOP_UP_FILL_KEY, TOP_UP_KEY


def handle_workpay_wallet_top_ups(df: pd.DataFrame, remarks_col: str, ref_col: str) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        top_up_mask = dataframe[remarks_col] == TOP_UP_KEY
        dataframe[ref_col] = dataframe[ref_col].astype(str)
        dataframe.loc[top_up_mask, ref_col] = TOP_UP_FILL_KEY
        return dataframe
    except Exception:
        raise