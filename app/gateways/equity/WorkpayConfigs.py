from typing import List


class WorkpayConfigs:
    EXCEL_SKIP_ROWS: int = 0
    CSV_SKIP_ROWS: int = 0
    SHEET_NAME: str = "KES"
    DATE_COLUMN: str = "DATE"
    API_REFERENCE_COLUMN: str = "API Reference"
    STATUS_COLUMN: str = "STATUS"
    REMARK_COLUMN:str = "REMARK"
    REFUND_KEY: str = "refunded"
    REFUND_FILTER: str = "Refund"
    TOP_UP_KEY: str = "Account Top Up"
    NUMERIC_COLUMNS: List[str] = ["AMOUNT", "SENDER FEE", "RECIPIENT FEE"]
    STRING_COLUMNS: List[str] = ["Transaction ID", "API Reference"]
    REQUIRED_COLUMNS = ["DATE", "Transaction ID", "API Reference", "AMOUNT"]
    WORKPAY_SLICE_COLUMNS = ["DATE", "Transaction ID", "API Reference", "RECIPIENT",  "AMOUNT", "STATUS",
                             "SENDER FEE", "RECIPIENT FEE", "Reconciliation Status", "Reconciliation Session"]

class WorkpayEquityConfigs(WorkpayConfigs):
    FILE_PREFIX = "equity_payouts"
    GATEWAY_NAME: str = "workpay_equity"
    MATCHING_COLUMN: str = "API Reference"

class WorkpayMpesaConfigs(WorkpayConfigs):
    FILE_PREFIX = "mpesa_payouts"
    GATEWAY_NAME: str = "workpay_mpesa"
    MATCHING_COLUMN: str = "Transaction ID"

class WorkpayKcbConfigs(WorkpayConfigs):
    FILE_PREFIX = "kcb_payouts"
    GATEWAY_NAME: str = "workpay_kcb"
    MATCHING_COLUMN: str = "Transaction ID"