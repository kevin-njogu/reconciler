from app.database.redis_configs import get_current_redis_session_id
from app.fileupload.services import get_uploads_dir

XLSX_ENGINE = "openpyxl"
XLS_ENGINE = "xlrd"
XLSX_EXTENSION = ".xlsx"
XLS_EXTENSION = ".xls"
CSV_EXTENSION = ".csv"
UNRECONCILED = "unreconciled"
RECONCILED = "reconciled"

def get_session():
    session_id = get_current_redis_session_id()
    return session_id
SESSION = get_session()

def get_directory():
    directory = get_uploads_dir(SESSION)
    return directory
UPLOADS_DIR=get_directory()

WP_COLS = {'date': 'DATE', 'tid': 'Transaction ID', 'ref': 'API Reference', 'method':'PAYMENT METHOD',
                  'account':'ACCOUNT NO./MOBILE', 'curr':'CURRENCY', 'amount': 'AMOUNT', 'sender_fee':'SENDER FEE',
                  'recipient_fee':'RECIPIENT FEE', 'recipient':'RECIPIENT', 'processing_status': 'STATUS', 'remark': 'REMARK',
                  'retries':'RETRIES', 'country':'COUNTRY'}

MPESA_COLUMNS = {"receipt_no": "Receipt No.", "completion_time": "Completion Time", "initiation_time": "Initiation Time", "details": "Details",
                 "status": "Transaction Status", "paid_in": "Paid In", "withdrawn": "Withdrawn", "balance": "Balance",
                 "balance_confirmed": "Balance Confirmed", "reason_type": "Reason Type", "other_party": "Other Party Info", "linked_tid": "Linked Transaction ID",
                 "account_no": "A/C No.", "currency": "Currency"}

KCB_COLUMNS = {"transaction_date": "Transaction Date", "value_date": "Value Date", "details": "Transaction Details", "money_out": "Money Out",
               "money_in": "Money In", "balance": "Ledger Balance", "reference": "Bank Reference Number"}


FILE_CONFIGS_WORKPAY_EQUITY= {"prefix":"equity_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}
FILE_CONFIGS_WORKPAY_MPESA= {"prefix":"mpesa_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}
FILE_CONFIGS_WORKPAY_KCB= {"prefix":"kcb_payouts", "excel_rows":0, "csv_rows":0, "sheet_name":"KES"}

FILE_CONFIGS_EQUITY = {"prefix":"1000", "excel_rows":8, "csv_rows":5, "sheet_name":0}
FILE_CONFIGS_MPESA = {"util_prefix":"ORG_939743_Utility", "mmf_prefix":"ORG_939743_MMF",  "excel_rows":6, "csv_rows":6, "sheet_name":0}
FILE_CONFIGS_KCB = {"kcb_prefix_excel":"accountTransaction", "kcb_prefix_csv":"transactionHistory", "excel_rows":14, "csv_rows":0, "sheet_name":0}

MMF_PREFIX = "ORG_939743_MMF"
UTILITY_PREFIX = "ORG_939743_Utility"


