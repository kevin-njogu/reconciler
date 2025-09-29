from fastapi import HTTPException

from .clean_data import equity_data_clean_up, workpay_equity_data_clean_up


def filter_equity_bank_charges(bank_data):
    try:
        mask = bank_data['NARRATIVE'].str.contains('CHARGE', case=False, na=False)
        equity_bank_charges = bank_data[mask]
        return equity_bank_charges
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to filter equity bank charges: {str(e)}")



def filter_equity_bank_credits(bank_data):
    try:
        mask = bank_data['CREDIT'] >= 1
        equity_bank_credits = bank_data[mask]
        return equity_bank_credits
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to filter equity bank credits: {str(e)}")



def filter_equity_bank_debits(bank_data):
    try:
        mask = bank_data['NARRATIVE'].str.contains('CHARGE', case=False, na=False)
        mask1 = bank_data['DEBIT'] >= 1
        equity_bank_debits = bank_data[~mask & mask1].copy()
        equity_bank_debits.insert(loc=3, column='REFERENCE', value="")
        for index, row in equity_bank_debits.iterrows():
            if row['NARRATIVE'].startswith('TPG'):
                split_narr = row['NARRATIVE'].split('/')
                api_reference = split_narr[-2]
                equity_bank_debits.loc[index, 'REFERENCE'] = api_reference
            elif row['NARRATIVE'].startswith('IFT'):
                split_narr = row['NARRATIVE'].split('_')
                api_reference = split_narr[0].replace('IFT', '')
                equity_bank_debits.loc[index, 'REFERENCE'] = api_reference
        return equity_bank_debits
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to filter equity bank debits: {str(e)}")


def match_transactions():
    try:
        original_equity_data = equity_data_clean_up()
        original_workpay_equity_data = workpay_equity_data_clean_up()

        if original_equity_data.empty or original_workpay_equity_data.empty:
            raise HTTPException(status_code=500, detail=f"Failed to match empty equity or workpay equity dataframe")

        equity_bank_debits = filter_equity_bank_debits(original_equity_data)
        workpay_equity_data = original_workpay_equity_data.copy()

        equity_matching_keys = equity_bank_debits['REFERENCE'].unique()
        backend_matching_keys = original_workpay_equity_data['REFERENCE'].unique()

        # Map STATUS directly from REFERENCE matching, don't overwrite REFERENCE
        equity_bank_debits['STATUS'] = equity_bank_debits['REFERENCE'].isin(backend_matching_keys).map({
            True: 'Reconciled',
            False: 'Unreconciled'
        })

        workpay_equity_data['STATUS'] = workpay_equity_data['REFERENCE'].isin(equity_matching_keys).map({
            True: 'Reconciled',
            False: 'Unreconciled'
        })

        return equity_bank_debits, workpay_equity_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to match transactions: {str(e)}")
