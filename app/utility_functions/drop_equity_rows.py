import pandas as pd

def drop_bottom_rows(df: pd.DataFrame) -> pd.DataFrame:
    try:
        dataframe = df.copy()

        # Find the index of the row containing the target string
        target_string = '----- End of Statement -----'
        mask = dataframe.apply(lambda row: row.astype(str).str.contains(target_string, case=False, na=False)).any(
            axis=1)

        if mask.any():
            first_match_idx = mask.idxmax()  # get first matching row index
            # Drop all rows from that row downward
            dataframe = dataframe.loc[:first_match_idx - 1]
        return dataframe
        # empty_rows = dataframe.isnull().all(axis=1)
        # first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(dataframe)
        # if empty_rows.any():
        #     return dataframe.loc[:first_empty_idx - 1]
        # else:
        #     return dataframe
    except Exception:
        raise