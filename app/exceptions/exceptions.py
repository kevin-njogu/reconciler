class MainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ControllerException(MainException):
    pass

class SessionServiceException(MainException):
    pass

class FileTypeException(MainException):
    pass

class EntityNotFoundException(MainException):
    pass

class EmptyDataException(MainException):
    pass

class ServiceExecutionException(MainException):
    pass

class NullValueException(MainException):
    pass