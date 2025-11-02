import uuid
import pandas as pd
from app.database.redis_configs import get_current_redis_session_id
from app.exceptions.exceptions import FileOperationsException
from app.utility_functions.constant_variables import REFUND_FILL_KEY, UNRECONCILED, TOP_UP_FILL_KEY
from app.utility_functions.handle_null_refs import handle_null_references_column
from app.utility_functions.handle_numerics import handle_numeric_columns
from app.utility_functions.handle_workpay_dates import handle_workpay_files_dates
from app.utility_functions.handle_workpay_refunds import handle_refunded_workpay
from app.utility_functions.handle_workpay_topups import handle_workpay_wallet_top_ups
from app.utility_functions.read_recon_files import read_file


def get_workpay_kcb_data(session_key: str, configs:dict) -> pd.DataFrame:
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


def clean_workpay_kcb_data(session_id: str, cols: dict, configs: dict) -> pd.DataFrame:
    try:
        new_df_cols = ['date', "transaction_id", "api_reference", "recipient", "amount", "sender_fee",
                       "recipient_fee", "processing_status", "remarks", "session"]

        session = cols.get("session")
        remarks = cols.get("remarks")
        date = cols.get("date")
        api_reference = cols.get('api_reference')
        transaction_id = cols.get("transaction_id")
        amount = cols.get('amount')
        sender_fee = cols.get('sender_fee')
        recipient_fee = cols.get("recipient_fee")
        processing_status = cols.get('processing_status')
        remark =  cols.get('remark')
        name = configs.get("name")
        date_format = "%Y-%m-%d %H:%M:%S"

        dataframe = get_workpay_kcb_data(session_id, configs)

        if dataframe.empty:
            raise FileOperationsException(f"Failed to clean empty workpay equity dataframe")

        dataframe = dataframe.iloc[:-1].copy()

        dataframe = handle_workpay_files_dates(dataframe, date, date_format)

        null_cols = [transaction_id, api_reference]
        dataframe = handle_null_references_column(dataframe, null_cols, name)

        dataframe = handle_workpay_wallet_top_ups(dataframe, remark, api_reference)

        dataframe = handle_refunded_workpay(dataframe, processing_status, remark, api_reference)

        numeric_cols = [amount, sender_fee, recipient_fee]
        dataframe = handle_numeric_columns(dataframe, numeric_cols)

        dataframe[api_reference] = (dataframe[api_reference].astype(str).str.split(".").str[0])
        dataframe[transaction_id] = (dataframe[transaction_id].astype(str).apply(
                lambda x: f"{name}-random_ref-{uuid.uuid4().hex[:8]}" if pd.isna(x) else x).astype(str))

        dataframe[remarks] = UNRECONCILED
        dataframe[session] = session_id

        #Create a clean dataframe
        cleaned_dataframe = pd.DataFrame(columns=new_df_cols)
        old_df_cols = [cols.get(k) for k in new_df_cols]
        cleaned_dataframe[new_df_cols] =  dataframe[old_df_cols]

        return cleaned_dataframe
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise


def get_workpay_kcb_payouts(df: pd.DataFrame, api_ref_col:str) -> pd.DataFrame:
    try:
        df = df.copy()
        wp_payouts = df.loc[~df[api_ref_col].isin([REFUND_FILL_KEY, TOP_UP_FILL_KEY])]
        return wp_payouts
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise


def get_workpay_kcb_refunds(df: pd.DataFrame, ref_col:str, remarks_col:str) -> pd.DataFrame:
    try:
        df = df.copy()
        wp_refunds = df.loc[df[ref_col] == REFUND_FILL_KEY]
        wp_refunds.loc[:, remarks_col] = REFUND_FILL_KEY
        return wp_refunds
    except KeyError as e:
        raise FileOperationsException(f"Invalid column: {e}")
    except Exception:
        raise

