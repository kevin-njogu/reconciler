import pandas as pd
from app.utility_functions.constant_variables import REFUND_FILL_KEY


def handle_refunded_workpay(df: pd.DataFrame, processing_status_col: str, remarks_col: str, ref_col: str) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        refund_mask_one = dataframe[processing_status_col] == "refunded"
        refund_mask_two = dataframe[remarks_col].str.contains("Refund")
        refund_mask = refund_mask_one | refund_mask_two
        dataframe.loc[refund_mask, ref_col] = REFUND_FILL_KEY
        return dataframe
    except Exception:
        raise
