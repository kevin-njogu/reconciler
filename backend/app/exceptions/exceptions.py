class MainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

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

class ColumnValidationException(MainException):
    pass


# --- Authentication Exceptions ---

class AuthException(MainException):
    """Base exception for authentication errors."""
    def __init__(self, message: str = "Authentication error", status_code: int = 401):
        super().__init__(message, status_code)


class InvalidCredentialsException(AuthException):
    """Raised when login credentials are invalid."""
    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message, 401)


class TokenExpiredException(AuthException):
    """Raised when a token has expired."""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, 401)


class InvalidTokenException(AuthException):
    """Raised when a token is invalid."""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, 401)


class PermissionDeniedException(MainException):
    """Raised when user lacks required permissions."""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 403)


class AccountBlockedException(MainException):
    """Raised when user account is blocked."""
    def __init__(self, message: str = "Account is blocked"):
        super().__init__(message, 403)


class AccountDeactivatedException(MainException):
    """Raised when user account is deactivated."""
    def __init__(self, message: str = "Account has been deactivated"):
        super().__init__(message, 403)


class PasswordChangeRequiredException(MainException):
    """Raised when user must change their password."""
    def __init__(self, message: str = "Password change required"):
        super().__init__(message, 403)