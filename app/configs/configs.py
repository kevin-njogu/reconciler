import redis

class Configs:
    REDIS = redis.Redis(host="localhost", db=0, port=6379, decode_responses=True)
    EXCEL_SUFFIX = ".xlsx"
    OLD_EXCEL_SUFFIX = ".xls"
    CSV_SUFFIX = ".csv"
    XLSX_ENGINE = "openpyxl"
    XLS_ENGINE = "xlrd"