import uuid

import pandas as pd

def handle_mpesa_tid(df:pd.DataFrame, tid_col: str) -> pd.DataFrame:
    try:
        dataframe = df.copy()
        mask_reversal = dataframe[tid_col].str.contains('000000')
        dataframe.loc[mask_reversal, tid_col] = (dataframe.loc[mask_reversal, tid_col].apply(
            lambda x: f"{x}-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str))
        return dataframe
    except Exception:
        raise
