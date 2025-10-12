import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz
from app.utils.extract_date_column import extract_date_column
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir
from app.configs.configs import Configs
from app.utils.read_excel import read_excel_files

sess = get_current_session()
dir_upl = get_uploads_dir(sess)

class Equity:

    def __init__(self, session, uploads_dir):
        self.session = session
        self.uploads_dir = uploads_dir
        self.prefix = "1000"
        self.skip_excel_rows = 8
        self.skip_csv_rows = 5
        self.sheet_name = 0
        self.gateway_cols = ["date", "narrative", "debit", "credit", "status"]


    def __drop_bottom_rows(self, df):
        empty_rows = df.isnull().all(axis=1)
        first_empty_idx = empty_rows.idxmax() if empty_rows.any() else len(df)
        if empty_rows.any():
            return df.loc[:first_empty_idx - 1]
        else:
            return df


    def __filter_debits(self, equity_df):
        try:
            bank_data = equity_df
            mask = bank_data['narrative'].str.contains('CHARGE', case=False, na=False)
            mask1 = bank_data['debit'] >= 1
            equity_bank_debits = bank_data[~mask & mask1].copy()
            equity_bank_debits.insert(loc=3, column='reference', value="")

            for index, row in equity_bank_debits.iterrows():
                if row['narrative'].startswith('TPG'):
                    split_narr = row['narrative'].split('/')
                    api_reference = split_narr[-2]
                    equity_bank_debits.loc[index, 'reference'] = api_reference
                elif row['narrative'].startswith('IFT'):
                    split_narr = row['narrative'].split('_')
                    api_reference = split_narr[0].replace('IFT', '')
                    equity_bank_debits.loc[index, 'reference'] = api_reference

            equity_bank_debits = equity_bank_debits.drop(columns=['credit','similarity'])

            #print(equity_bank_debits)
            return equity_bank_debits
        except Exception as e:
            raise HTTPException(status_code=500, detail=e)


    def __filter_credits(self, equity_df):
        try:
            mask = equity_df['credit'] >= 1
            equity_bank_credits = equity_df[mask]
            equity_bank_credits.loc[:, 'status'] = 'Reconciled'
            equity_bank_credits = equity_bank_credits.drop(columns=['debit', 'similarity'])

            return equity_bank_credits
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def __filter_charges(self, equity_df):
        try:
            threshold = 70
            keyword = "CHARGE"
            equity_df['similarity'] = equity_df['narrative'].apply(
                lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower())
            )
            mask = equity_df['similarity'] >= threshold
            equity_bank_charges = equity_df[mask].copy()
            equity_bank_charges.loc[:, 'status'] = 'Reconciled'
            equity_bank_charges = equity_bank_charges.drop(columns=['debit', "similarity"])

            return equity_bank_charges
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def read_file(self):
        equity_dataframe = pd.DataFrame()
        xlsx_engine = Configs.XLSX_ENGINE
        xls_engine = Configs.XLS_ENGINE

        try:
            for file in self.uploads_dir.iterdir():
                if not file:
                    raise HTTPException(status_code=404, detail="no files found in uploads dir")

                if file.name.startswith(self.prefix):
                    if file.suffix == Configs.EXCEL_SUFFIX:
                        equity_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                                   engine=xlsx_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.OLD_EXCEL_SUFFIX:
                        equity_dataframe = read_excel_files(file, sheet_name=self.sheet_name,
                                                                   engine=xls_engine, skip_rows=self.skip_excel_rows)
                        break
                    elif file.suffix == Configs.CSV_SUFFIX:
                        equity_dataframe = pd.read_csv(file, skiprows=self.skip_csv_rows)
                        break
                    else:
                        raise HTTPException(status_code=400, detail="file type not supported")

            if equity_dataframe.empty:
                raise HTTPException(status_code=400, detail="equity dataframe is empty")

            # print(equity_dataframe.columns)
            return equity_dataframe

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def clean_data(self):
        equity_dataframe = pd.DataFrame()
        try:
            raw_df = self.read_file()
            if 'Unnamed: 0' in raw_df.columns:
                dropped_first_two_cols_df = raw_df.iloc[:, 2:]
                dropped_last_rows_df = self.__drop_bottom_rows(dropped_first_two_cols_df)
                final_raw_df = convert_columns_to_numeric(dropped_last_rows_df, ['Debit', 'Credit'])

                equity_dataframe = pd.DataFrame(columns=self.gateway_cols)
                equity_dataframe["date"] = extract_date_column(final_raw_df,["Transaction Date", "Value Date"])
                equity_dataframe[["narrative", "debit", "credit"]] = final_raw_df[["Narrative", "Debit", "Credit"]]
                equity_dataframe["status"] = "Unreconciled"
            else:
                equity_dataframe = raw_df

            # print(equity_dataframe['credit'])
            return equity_dataframe
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def filter_data(self):
        equity_df = self.clean_data()

        charges_df = self.__filter_charges(equity_df)
        credits_df = self.__filter_credits(equity_df)
        debits_df = self.__filter_debits(equity_df)

        # print(debits_df)

        return charges_df, credits_df, debits_df



# equity = Equity(sess, dir_upl)
# equity.read_file()
# equity.clean_data()
# equity.filter_data()