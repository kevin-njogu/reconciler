class MainException(Exception):
    def __init__(self, message: str):
        self.message = message

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