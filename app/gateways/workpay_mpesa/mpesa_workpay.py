import uuid

from fastapi import HTTPException
import pandas as pd

from app.configs.configs import Configs
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.utils.read_excel import read_excel_files

# sess = get_current_session()#
# dir_uploads = get_uploads_dir(sess)

class MpesaWorkpay:

    def __init__(self, session, uploads_dir):
        self.prefix = "mpesa_payout"
        self.sheet_name = "KES"
        self.session = session
        self.uploads_dir = uploads_dir
        self.gateway_cols = ["date", "reference", "method", "debit", "sender", "recipient", "status"]


    def __fill_transaction_id(self, row):

        if pd.isna(row["Transaction ID"]) or row["Transaction ID"] == "":
            if pd.notna(row["API Reference"]) and row["API Reference"] != "":
                return row["API Reference"]
            else:
                return f'random{str(uuid.uuid4())[:8]}'  # generate short random string
        return row["Transaction ID"]


    def read_file(self):

        mpesa_workpay_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        mpesa_workpay_dataframe= read_excel_files(file, sheet_name=self.sheet_name, engine=xlsx_engine)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        mpesa_workpay_dataframe = read_excel_files(file, sheet_name=self.sheet_name, engine=xls_engine)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        mpesa_workpay_dataframe = pd.read_csv(file)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if mpesa_workpay_dataframe.empty:
                raise HTTPException(status_code=400, detail="mpesa workpay dataframe is empty")

            # print(mpesa_workpay_dataframe)
            return mpesa_workpay_dataframe

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        try:
            raw_df = self.read_file()
            dropped_last_row_df = raw_df.iloc[:-1]
            dropped_last_row_df_copy = dropped_last_row_df.copy()
            dropped_last_row_df_copy.loc[:, 'DATE'] = pd.to_datetime(dropped_last_row_df['DATE'])
            dropped_last_row_df_copy.loc[:, ['AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']] = (
                dropped_last_row_df_copy[['AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']]
                .apply(pd.to_numeric, errors='coerce').fillna(0))
            dropped_last_row_df_copy.loc[:, "Transaction ID"] = (dropped_last_row_df_copy["Transaction ID"].astype(str)
                                                                 .replace('nan', pd.NA))
            dropped_last_row_df_copy["Transaction ID"] = dropped_last_row_df_copy.apply(self.__fill_transaction_id, axis=1)
            dropped_last_row_df_copy["Transaction ID"] = dropped_last_row_df_copy["Transaction ID"].astype(str)

            mpesa_workpay = pd.DataFrame(columns=self.gateway_cols)
            mpesa_workpay[["date", "reference", "method", "debit", "sender", "recipient"]] = (
                dropped_last_row_df_copy)[['DATE', 'Transaction ID', 'PAYMENT METHOD', 'AMOUNT', 'SENDER FEE', 'RECIPIENT FEE']]
            mpesa_workpay['status'] = 'Unreconciled'

            # print( mpesa_workpay.columns)
            return  mpesa_workpay
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


# wp_mpesa = MpesaWorkpay(sess, dir_uploads)
# wp_mpesa.read_file()
# wp_mpesa.clean_data()

