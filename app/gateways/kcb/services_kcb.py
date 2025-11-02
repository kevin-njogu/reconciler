import re
from typing import List

import pandas as pd

from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import FileOperationsException
from app.utility_functions.assign_ref_column import assign_reference_column
from app.utility_functions.constant_variables import UNRECONCILED, DEPOSITS, CHARGES
from app.utility_functions.handle_gateway_dates import handle_gateway_date_columns
from app.utility_functions.handle_null_refs import handle_null_references_column
from app.utility_functions.handle_numerics import handle_numeric_columns
from app.utility_functions.read_recon_files import read_file


def get_kcb_data(session_key: str, configs:dict) -> pd.DataFrame:
    try:
        df = read_file(session_id=session_key,
                       filename_prefix=configs.get("prefix"),
                       sheet_name=configs.get("sheet_name"),
                       excel_skip_rows=configs.get("excel_rows"),
                       csv_skip_rows=configs.get("csv_rows")
                       )
        return df
    except Exception:
        raise


def clean_kcb_data(session_key: str, configs: dict,  gateway_columns:dict) -> pd.DataFrame:
    try:
        new_cols = ["date", "details", "reference", "debits", "credits", "remarks", "session"]
        unnamed_columns = ['Unnamed: 0', 'Unnamed: 1']
        transaction_date = gateway_columns.get("transaction_date")
        value_date = gateway_columns.get("value_date")
        new_date = gateway_columns.get("date")
        debits = gateway_columns.get("debits")
        credits =  gateway_columns.get("credits")
        reference = gateway_columns.get("reference")
        details = gateway_columns.get("details")
        name = configs.get('name')
        remarks = gateway_columns.get("remarks")
        session = gateway_columns.get("session")
        date_format = "%d.%m.%Y"

        df = get_kcb_data(session_key, configs)

        if df.empty:
            raise FileOperationsException(f"Failed to clean empty equity dataframe")

        current_date = transaction_date if transaction_date in df.columns else value_date
        df = handle_gateway_date_columns(df, current_date, new_date, date_format)

        numeric_columns = [debits, credits]
        for col in numeric_columns:
            if col not in df.columns:
                raise FileOperationsException(f"{col} column is missing in your file")
        df = handle_numeric_columns(df, numeric_columns)

        df = assign_reference_column(df, reference, details)

        str_cols = [reference, details]
        df = handle_null_references_column(df, str_cols, name)

        df[remarks] = UNRECONCILED
        df[session] = session_key

        final_dataframe = pd.DataFrame(columns=new_cols)
        old_cols =  [gateway_columns.get(col) for col in new_cols]
        final_dataframe[new_cols] = df[old_cols]
        return final_dataframe
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise


def get_kcb_debits(df: pd.DataFrame, details_col: str, debits_col: str, reference_col: str) -> pd.DataFrame:
    try:
        charges_keys = ["Transfer Charge"]

        dataframe = df.copy()
        mask = dataframe[details_col].str.contains('|'.join(map(re.escape, charges_keys)), case=False, na=False)
        mask1 = dataframe[debits_col] >= 1
        debits_dataframe = dataframe[~mask & mask1]
        for idx,ref in debits_dataframe[details_col].items():
            if not isinstance(ref, str):
                continue
            ref = ref.strip()
            parts = ref.split(" ")
            api_ref = parts[1].strip() if len(parts) >= 2 else ref
            debits_dataframe.loc[idx, reference_col] = api_ref
        return debits_dataframe
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise


def get_kcb_credits(df: pd.DataFrame, credits_col: str, remarks_col: str) -> pd.DataFrame:
    try:
        dataframe = df
        mask = dataframe[credits_col] >= 1
        credits_dataframe = dataframe[mask]
        credits_dataframe.loc[:, remarks_col] = DEPOSITS
        return credits_dataframe
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise


def get_kcb_charges(df:pd.DataFrame, details_col: str, credits_col:str, remarks_col:str) -> pd.DataFrame:
    try:
        charges_keys = ["Transfer Charge"]
        dataframe = df.copy()
        mask = dataframe[details_col].str.contains('|'.join(map(re.escape, charges_keys)), case=False, na=False)
        mask1 = dataframe[credits_col] == 0
        charges_dataframe = dataframe[mask & mask1]
        charges_dataframe.loc[:, remarks_col] = CHARGES
        return charges_dataframe
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise