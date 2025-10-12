import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz
from app.utils.extract_date_column import extract_date_column
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.configs.configs import Configs
from app.utils.read_excel import read_excel_files

# sess = get_current_session()
# dir_upl = get_uploads_dir(sess)

class KCB:

    def __init__(self, session, uploads_dir):
        self.session = session
        self.uploads_dir = uploads_dir
        self.prefix = "accountTransaction"
        self.skip_excel_rows = 14
        self.skip_csv_rows = 0
        self.sheet_name = 0
        self.gateway_cols = ["date", "narrative", "debit", "credit", "status"]


    def __filter_debits(self, kcb_df):
        try:
            kcb_api_refs = []
            mask1 = kcb_df['narrative'].str.contains('Charge', case=False, na=False)
            mask2 = kcb_df['debit'] > 0
            kcb_debits = kcb_df[mask2 & ~mask1]
            for index, row in kcb_debits.iterrows():
                split_narr = row['narrative'].split(' ')
                kcb_api_refs.append(split_narr[2].strip())
            kcb_debits.insert(loc=3, column='reference', value=kcb_api_refs)
            kcb_debits = kcb_debits.drop(columns=['credit', 'similarity'])

            return kcb_debits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_credits(self, kcb_df):
        try:
            mask = kcb_df['credit'] >= 1
            kcb_credits = kcb_df[mask]
            kcb_credits.loc[:, 'status'] = 'Reconciled'
            kcb_credits = kcb_credits.drop(columns=['debit', 'similarity'])

            return kcb_credits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_charges(self, kcb_df):
        threshold = 70
        try:
            keyword = "Charge"
            kcb_df['similarity'] = kcb_df['narrative'].apply(
                lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower())
            )
            mask = kcb_df['similarity'] >= threshold
            kcb_charges = kcb_df[mask].copy()
            kcb_charges.loc[:, 'status'] = 'Reconciled'
            kcb_charges = kcb_charges.drop(columns=["credit", "similarity"])

            return kcb_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def read_file(self):
        kcb_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        kcb_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                                   engine=xlsx_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        kcb_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                                   engine=xls_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        kcb_dataframe = pd.read_csv(file, skiprows=self.skip_csv_rows)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if kcb_dataframe.empty:
                raise HTTPException(status_code=400, detail="kcb dataframe is empty")

            # print(kcb_dataframe.columns)
            return kcb_dataframe
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        try:
            raw_df = self.read_file()
            dropped_first_row_df = raw_df.iloc[1:]
            for col in ['Money Out', 'Money In']:
                dropped_first_row_df.loc[:, col] = dropped_first_row_df[col].str.replace(',', '')
                dropped_first_row_df.loc[:, col] = pd.to_numeric(dropped_first_row_df[col], errors="coerce").fillna(0)

            dropped_first_row_df.loc[:, "Value Date"] = dropped_first_row_df["Value Date"].astype(str).str.strip()
            dropped_first_row_df.loc[:, "Transaction Date"] = dropped_first_row_df["Transaction Date"].astype(
                str).str.strip()
            kcb_dataframe = pd.DataFrame(columns=self.gateway_cols)
            kcb_dataframe['date'] = extract_date_column(dropped_first_row_df,
                                                ["Transaction Date", "Value Date"], format("%d.%m.%Y"))
            # deduped_df = dropped_first_row_df.drop_duplicates(subset=["Transaction Details"], keep="first")
            kcb_dataframe[["narrative", "debit", "credit"]] = dropped_first_row_df[["Transaction Details", "Money Out", "Money In"]]
            kcb_dataframe.loc[:, 'debit'] = (kcb_dataframe['debit'] * -1)
            kcb_dataframe["status"] = "Unreconciled"

            # print(kcb_dataframe)
            return kcb_dataframe
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def filter_data(self):
        kcb_df = self.clean_data()

        charges_df = self.__filter_charges(kcb_df)
        credits_df = self.__filter_credits(kcb_df)
        debits_df = self.__filter_debits(kcb_df)

        # print(charges_df.columns)

        return charges_df, credits_df, debits_df

# kcb = KCB(sess, dir_upl)
# kcb.read_file()
# kcb.clean_data()
# kcb.filter_data()