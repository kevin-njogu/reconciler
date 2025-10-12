import uuid

from fastapi import HTTPException
import pandas as pd
from app.configs.configs import Configs
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.utils.read_excel import read_excel_files

sess = get_current_session()
dir_uploads = get_uploads_dir(sess)

class EquityWorkpay:

    def __init__(self, session, uploads_dir):
        self.prefix = "equity_payout"
        self.sheet_name = "KES"
        self.session = session
        self.uploads_dir = uploads_dir
        self.gateway_cols = ["date", "reference", "method", "debit", "sender", "recipient", "status"]

    def __fill_api_ref(self, row):
        if pd.isna(row["API Reference"]) or row["API Reference"] == "":
            if pd.notna(row["Transaction ID"]) and row["Transaction ID"] != "":
                return row["Transaction ID"]
            else:
                return f'random{str(uuid.uuid4())[:8]}'  # generate short random string
        return row["API Reference"]


    def __generate_random_str(self):
        random_str = f"random{uuid.uuid4().hex[:8]}"
        return random_str


    def read_file(self):

        equity_workpay_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        equity_workpay_dataframe= read_excel_files(file, sheet_name=self.sheet_name, engine=xlsx_engine)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        equity_workpay_dataframe = read_excel_files(file, sheet_name=self.sheet_name, engine=xls_engine)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        equity_workpay_dataframe = pd.read_csv(file)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if equity_workpay_dataframe.empty:
                raise HTTPException(status_code=400, detail="Equity workpay dataframe is empty")

            # print(equity_workpay_dataframe)
            return equity_workpay_dataframe

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        random_str = self.__generate_random_str()
        try:
            raw_df = self.read_file()
            dropped_last_row_df = raw_df.iloc[:-1]
            dropped_last_row_df_copy = dropped_last_row_df.copy()
            dropped_last_row_df_copy.loc[:, 'DATE'] = pd.to_datetime(dropped_last_row_df['DATE'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
            dropped_last_row_df_copy.loc[:, ['AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']] = (
                dropped_last_row_df_copy[['AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']]
                .apply(pd.to_numeric, errors='coerce').fillna(0))
            dropped_last_row_df_copy = dropped_last_row_df_copy.astype({'API Reference': 'object'})
            dropped_last_row_df_copy.loc[:, "API Reference"] = (dropped_last_row_df_copy["API Reference"].astype(str)
                                                                 .replace('nan', pd.NA))
            dropped_last_row_df_copy['API Reference'] = (dropped_last_row_df_copy['API Reference'].astype(str)
                                                         .str.split(".").str[0])
            dropped_last_row_df_copy['API Reference'] =  dropped_last_row_df_copy.apply(self.__fill_api_ref, axis=1)
            dropped_last_row_df_copy['API Reference'] = dropped_last_row_df_copy['API Reference'].apply(
                lambda x: f"random{uuid.uuid4().hex[:8]}" if pd.isna(x) or x == '<NA>' else x)
            dropped_last_row_df_copy.loc[:, 'PAYMENT METHOD'] = (dropped_last_row_df_copy['PAYMENT METHOD'].apply(
                lambda x: f"random{uuid.uuid4().hex[:8]}" if pd.isna(x) or x == '<NA>' else x))

            equity_workpay = pd.DataFrame(columns=self.gateway_cols)
            equity_workpay[["date", "reference", "method", "debit", "sender", "recipient"]] = (
                dropped_last_row_df_copy[['DATE', 'API Reference', 'PAYMENT METHOD', 'AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']])
            equity_workpay['status'] = 'Unreconciled'

            # print(equity_workpay['reference'])
            return equity_workpay
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


# wp_equity = EquityWorkpay(sess, dir_uploads)
# wp_equity.read_file()
# wp_equity.clean_data()

