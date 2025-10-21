from app.database.redis_configs import get_current_redis_session_id
from app.fileupload.services import get_uploads_dir

XLSX_ENGINE = "openpyxl"
XLS_ENGINE = "xlrd"
XLSX_EXTENSION = ".xlsx"
XLS_EXTENSION = ".xls"
CSV_EXTENSION = ".csv"
UNRECONCILED = "unreconciled"
RECONCILED = "reconciled"


WP_COLS = {'date': 'DATE', 'tid': 'Transaction ID', 'ref': 'API Reference', 'method':'PAYMENT METHOD',
                  'account':'ACCOUNT NO./MOBILE', 'curr':'CURRENCY', 'amount': 'AMOUNT', 'sender_fee':'SENDER FEE',
                  'recipient_fee':'RECIPIENT FEE', 'recipient':'RECIPIENT', 'processing_status': 'STATUS', 'remark': 'REMARK',
                  'retries':'RETRIES', 'country':'COUNTRY'}
FILE_CONFIGS_WORKPAY_EQUITY= {"prefix":"equity_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}
FILE_CONFIGS_WORKPAY_MPESA= {"prefix":"mpesa_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}
FILE_CONFIGS_WORKPAY_KCB= {"prefix":"kcb_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}

MPESA_COLUMNS = {"date":"date", "reference": "Receipt No.", "value_date": "Completion Time", "transaction_date": "Initiation Time", "details": "Details",
                 "status": "Transaction Status", "credits": "Paid In", "debits": "Withdrawn", "balance": "Balance",
                 "balance_confirmed": "Balance Confirmed", "reason_type": "Reason Type", "other_party": "Other Party Info", "linked_tid": "Linked Transaction ID",
                 "account_no": "A/C No.", "currency": "Currency"}
FILE_CONFIGS_MPESA = {"util_prefix":"ORG_939743_Utility", "mmf_prefix":"ORG_939743_MMF",  "excel_rows":6, "csv_rows":6, "sheet_name":0}
FILE_CONFIGS_MMF = {"name":"mmf", "prefix":"ORG_939743_MMF",  "excel_rows":6, "csv_rows":6, "sheet_name":0}
FILE_CONFIGS_UTILITY = {"name": "utility", "prefix":"ORG_939743_Utility", "excel_rows":6, "csv_rows":6, "sheet_name":0}


KCB_COLUMNS = {"date":"date", "transaction_date": "Transaction Date", "value_date": "Value Date", "details": "Transaction Details", "debits": "Money Out",
               "credits": "Money In", "balance": "Ledger Balance", "reference": "Bank Reference Number"}
FILE_CONFIGS_KCB = {"name": "kcb", "prefix":"accountTransaction", "excel_rows":14, "csv_rows":0, "sheet_name":0}


EQUITY_COLUMNS = {"date":"date", "transaction_date": "Transaction Date", "value_date": "Value Date", "details": "Narrative", "reference": "Customer Reference",
                  "debits": "Debit", "credits": "Credit"}
FILE_CONFIGS_EQUITY = {"name": "equity", "prefix":"1000", "excel_rows":8, "csv_rows":5, "sheet_name":0}



MMF_PREFIX = "ORG_939743_MMF"
UTILITY_PREFIX = "ORG_939743_Utility"


