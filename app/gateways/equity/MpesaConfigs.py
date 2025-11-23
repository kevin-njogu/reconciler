from typing import Union, List


class MpesaConfigs:
    FILE_PREFIX=None
    BANK_EXCEL_SKIP_ROWS: int = 6
    BANK_CSV_SKIP_ROWS: int = 6
    DATE_COLUMN: str = "Completion Time"
    NARRATIVE_COLUMN: str = "Details"
    DEBIT_COLUMN:str = "Withdrawn"
    CREDIT_COLUMN: str = "Paid In"
    DATE_FORMAT: str = "%d-%m-%Y %H:%M:%S"
    GATEWAY_NAME: str = "mpesa"
    MATCHING_COLUMN: str = "Receipt No."
    BANK_SHEET_NAME: Union[str|int] = 0
    MPESA_PREFIXES: List[str] = ["ORG_939743_Utility", "ORG_939743_MMF"]
    CHARGES_FILTER_KEY: List[str] = ["Business Pay Bill Charge", "Business Buy Goods Charge", "B2C Payment Charge"]
    NUMERIC_COLUMNS: List[str] = ["Withdrawn", "Paid In", "Balance"]
    STRING_COLUMNS: List[str] = [ "Details", "Receipt No.",]
    REQUIRED_COLUMNS: List[str] = ["Completion Time", "Details", "Receipt No.", "Withdrawn", "Paid In", "Balance"]
    GATEWAY_SLICE_COLUMNS: List[str] = ["Receipt No.", "Completion Time", "Details",
                                        "Paid In", "Withdrawn", "Reconciliation Status", "Reconciliation Session"]


class UtilityConfigs(MpesaConfigs):
    FILE_PREFIX = "ORG_939743_Utility"


class MmfConfigs(MpesaConfigs):
    FILE_PREFIX = "ORG_939743_MMF"