import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz
from app.configs.configs import Configs
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.utils.read_excel import read_excel_files

# sess = get_current_session()
# dir_uploads = get_uploads_dir(sess)

class MpesaUtility:

    def __init__(self, session, uploads_dir):
        self.session = session
        self.uploads_dir = uploads_dir
        self.prefix = "ORG_939743_Utility"
        self.sheet_name = 0
        self.skip_excel_rows = 6
        self.skip_csv_rows =  6
        self.gateway_cols = ["date", "narrative", "details", "debit", "credit", "status"]


    def __filter_debits(self, utility_df):
        threshold = 70
        try:
            keyword = "B2C Payment Charge"
            utility_df['similarity'] = utility_df['details'].apply(
                lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower())
            )
            mask = utility_df['similarity'] >= threshold
            mask1 = utility_df['credit'] > 0
            utility_debits = utility_df[~mask & ~mask1].copy()
            negative_mask = utility_debits['debit'] < 0
            utility_debits.loc[negative_mask, 'debit'] = utility_debits.loc[negative_mask, 'debit'] * -1
            utility_debits.loc[:, 'status'] = 'Unreconciled'
            utility_debits = utility_debits.drop(columns=["credit", "similarity"])

            return utility_debits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_charge(self, utility_df):
        threshold = 70
        try:
            keyword = "B2C Payment Charge"
            utility_df['similarity'] = utility_df['details'].apply(
                lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower())
            )
            mask = utility_df['similarity'] >= threshold
            mask1 = utility_df['credit'] > 0
            utility_charges = utility_df[mask & ~mask1].copy()
            negative_mask =  utility_charges['debit'] < 0
            utility_charges.loc[negative_mask, 'debit'] =  utility_charges.loc[negative_mask, 'debit'] * -1
            utility_charges.loc[:, 'status'] = 'Reconciled'
            utility_charges =  utility_charges.drop(columns=["credit","similarity"])

            # print(utility_charges)
            return  utility_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_credits(self, utility_df):
        try:
            mask = utility_df['credit'] > 0
            utility_credits = utility_df[mask].copy()
            utility_credits['status'] = 'Reconciled'
            utility_credits= utility_credits.drop(columns=["debit", "similarity"])

            # print(utility_credits)
            return utility_credits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def read_file(self):

        mpesa_utility_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        mpesa_utility_dataframe= read_excel_files(file, sheet_name=self.sheet_name,
                                                            engine=xlsx_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        mpesa_utility_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                            engine=xls_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        mpesa_utility_dataframe = pd.read_csv(file, skiprows=self.skip_csv_rows)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if mpesa_utility_dataframe.empty:
                raise HTTPException(status_code=400, detail="utility dataframe is empty")

            # print(mpesa_utility_dataframe.columns)
            return mpesa_utility_dataframe

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        try:
            raw_df = self.read_file()
            raw_df.loc[:, 'Completion Time'] = pd.to_datetime(raw_df['Completion Time'],
                                                                   format="%d-%m-%Y %H:%M:%S", errors='coerce')
            raw_df.loc[:, ['Withdrawn', 'Paid In']] =  raw_df[['Withdrawn', 'Paid In']].fillna(0)
            mpesa_utility_df = pd.DataFrame(columns=self.gateway_cols)
            mpesa_utility_df[['date', 'narrative', 'details', 'debit', 'credit']] = (
                raw_df)[['Completion Time', 'Receipt No.', 'Details', 'Withdrawn', 'Paid In']]
            mpesa_utility_df['status'] = 'Unreconciled'

            # print(mpesa_utility_df)
            return mpesa_utility_df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def filter_data(self):
        utility_df = self.clean_data()

        debits_df = self.__filter_debits(utility_df)
        charge_df = self.__filter_charge(utility_df)
        credits_df = self.__filter_credits(utility_df)

        # print(charge_df.columns)

        return charge_df, credits_df, debits_df



# utility = MpesaUtility(sess, dir_uploads)
# utility.read_file()
# utility.clean_data()
# utility.filter_data()

