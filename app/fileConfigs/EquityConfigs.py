from typing import Union, List


class EquityConfigs:
    FILE_PREFIX: str = "Account_statement"
    BANK_EXCEL_SKIP_ROWS: int = 8
    BANK_CSV_SKIP_ROWS: int = 5
    DATE_COLUMN: str = "Transaction Date"
    NARRATIVE_COLUMN: str = "Narrative"
    DEBIT_COLUMN:str = "Debit"
    CREDIT_COLUMN: str = "Credit"
    DATE_FORMAT: str = "%d/%m/%Y"
    GATEWAY_NAME: str = "equity"
    MATCHING_COLUMN: str = "Customer Reference"
    BANK_SHEET_NAME: Union[str|int] = 0
    CHARGES_FILTER_KEY: List[str] = ["JENGA CHARGE", "EFT Comm"]
    NUMERIC_COLUMNS: List[str] = ["Debit", "Credit", "Running Balance"]
    STRING_COLUMNS: List[str] = ["Narrative", "Transaction Reference", "Customer Reference"]
    REQUIRED_COLUMNS: List[str] = ["Transaction Date", "Narrative", "Transaction Reference",
                        "Customer Reference", "Debit", "Credit", "Running Balance"]
    GATEWAY_SLICE_COLUMNS: List[str] = ["Transaction Date", "Narrative", "Transaction Reference", "Customer Reference",
                                   "Debit", "Credit", "Reconciliation Status", "Reconciliation Session"]

