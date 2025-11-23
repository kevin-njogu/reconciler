from typing import Union, List


class KcbConfigs:
    FILE_PREFIX: str = "accountTransaction"
    BANK_EXCEL_SKIP_ROWS: int = 14
    BANK_CSV_SKIP_ROWS: int = 0
    DATE_COLUMN: str = "Transaction Date"
    NARRATIVE_COLUMN: str = "Transaction Details"
    DEBIT_COLUMN:str = "Money Out"
    CREDIT_COLUMN: str = "Money In"
    DATE_FORMAT: str = " %d.%m.%Y"
    GATEWAY_NAME: str = "kcb"
    MATCHING_COLUMN: str = "Bank Reference Number"
    BANK_SHEET_NAME: Union[str|int] = 0
    CHARGES_FILTER_KEY: List[str] = ["Transfer Charge"]
    NUMERIC_COLUMNS: List[str] = ["Money Out", "Money In", "Ledger Balance"]
    STRING_COLUMNS: List[str] = [ "Transaction Details", "Bank Reference Number",]
    REQUIRED_COLUMNS: List[str] = ["Transaction Date", "Transaction Details", "Bank Reference Number",
                                   "Money Out", "Money In", "Ledger Balance"]
    GATEWAY_SLICE_COLUMNS: List[str] = ["Transaction Date", "Transaction Details", "Bank Reference Number",
                                   "Money Out", "Money In", "Reconciliation Status", "Reconciliation Session"]

