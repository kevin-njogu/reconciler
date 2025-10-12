import pandas as pd
from fastapi import HTTPException
from app.configs.configs import Configs
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.utils.read_excel import read_excel_files

# sess = get_current_session()
# dir_uploads = get_uploads_dir(sess)

class MpesaMmf:

    def __init__(self, session, uploads_dir):
        self.session = session
        self.uploads_dir = uploads_dir
        self.prefix = "ORG_939743_MMF"
        self.sheet_name = 0
        self.skip_excel_rows = 6
        self.skip_csv_rows =  6
        self.gateway_cols = ["date", "narrative", "details", "debit", "credit", "status"]


    def __filter_debits(self, mmf_df):
        try:
            filter_str_one = "Business Pay Bill Charge"
            filter_str_two = "Business Buy Goods Charge"

            mask1 = mmf_df['details'].str.contains(filter_str_one, case=False, na=False)
            mask2 = mmf_df['details'].str.contains(filter_str_two, case=False, na=False)
            mask3 = mmf_df['credit'] > 0
            mmf_debits = mmf_df[~mask3 & ~mask1 & ~mask2].copy()

            # convert paid out amounts from -ve to +ve
            negative_mask = mmf_debits['debit'] < 0
            mmf_debits.loc[negative_mask, 'debit'] = mmf_debits.loc[negative_mask, 'debit'] * -1
            mmf_debits = mmf_debits.drop(columns=['credit'])

            return mmf_debits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_charge(self, mmf_df):
        try:
            filter_str_one = "Business Pay Bill Charge"
            filter_str_two = "Business Buy Goods Charge"

            mask1 = mmf_df['details'].str.contains(filter_str_one, case=False, na=False)
            mask2 = mmf_df['details'].str.contains(filter_str_two, case=False, na=False)
            mmf_charges = mmf_df[mask1 | mask2].copy()
            mmf_charges['status'] = 'Reconciled'
            mmf_charges = mmf_charges.drop(columns=['credit'])

            return  mmf_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_credits(self, mmf_df):
        try:
            mask1 = mmf_df['credit'] > 0
            mmf_credits = mmf_df[mask1].copy()
            mmf_credits['status'] = 'Reconciled'
            mmf_credits = mmf_credits.drop(columns=['debit'])

            return mmf_credits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def read_file(self):

        mpesa_mmf_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        mpesa_mmf_dataframe= read_excel_files(file, sheet_name=self.sheet_name,
                                                            engine=xlsx_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        mpesa_mmf_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                            engine=xls_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        mpesa_mmf_dataframe = pd.read_csv(file, skiprows=self.skip_csv_rows)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if mpesa_mmf_dataframe.empty:
                raise HTTPException(status_code=400, detail="mmf dataframe is empty")

            # print(mpesa_mmf_dataframe.columns)
            return mpesa_mmf_dataframe

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        try:
            raw_df = self.read_file()
            raw_df.loc[:, 'Completion Time'] = pd.to_datetime(raw_df['Completion Time'],
                                                                   format="%d-%m-%Y %H:%M:%S", errors='coerce')
            raw_df.loc[:, ['Withdrawn', 'Paid In']] =  raw_df[['Withdrawn', 'Paid In']].fillna(0)
            mpesa_mmf_df = pd.DataFrame(columns=self.gateway_cols)
            mpesa_mmf_df[['date', 'narrative', 'details', 'debit', 'credit']] = (
                raw_df)[['Completion Time', 'Receipt No.', 'Details', 'Withdrawn', 'Paid In']]
            mpesa_mmf_df['status'] = 'Unreconciled'

            # print(mpesa_mmf_df)
            return mpesa_mmf_df
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def filter_data(self):
        mmf_df = self.clean_data()

        debits_df = self.__filter_debits(mmf_df)
        charge_df = self.__filter_charge(mmf_df)
        credits_df = self.__filter_credits(mmf_df)

        # print(credits_df.columns)

        return charge_df, credits_df, debits_df


# mmf = MpesaMmf(sess, dir_uploads)
# mmf.read_file()
# mmf.clean_data()
# mmf.filter_data()

