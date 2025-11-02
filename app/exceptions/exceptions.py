class MainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class RedisException(MainException):
    pass

class FileUploadException(MainException):
    pass

class ReadFileException(MainException):
    pass

class FileOperationsException(MainException):
    pass

class ReconciliationException(MainException):
    pass

class DbOperationException(MainException):
    pass