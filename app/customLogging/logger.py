"""
Logger Utility Module.

Provides convenient access to loggers with consistent naming conventions.
Use this module to get loggers throughout the application.
"""
import logging
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128)
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name. If None, returns the root app logger.
              Use module __name__ for module-specific loggers.

    Returns:
        Configured logger instance.

    Examples:
        # Get module-specific logger
        logger = get_logger(__name__)

        # Get named logger
        logger = get_logger("app.controller.upload")

        # Get root app logger
        logger = get_logger()
    """
    if name is None:
        return logging.getLogger("app")
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin class that provides a logger property.

    Add this mixin to any class to get automatic logger access.

    Example:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")
    """

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__)


def log_operation(
    logger: logging.Logger,
    operation: str,
    success: bool = True,
    **context
) -> None:
    """
    Log an operation with consistent format.

    Args:
        logger: Logger instance to use.
        operation: Name of the operation being logged.
        success: Whether the operation succeeded.
        **context: Additional context to include in the log.

    Example:
        log_operation(logger, "file_upload", success=True, file_name="data.xlsx", size=1024)
    """
    level = logging.INFO if success else logging.ERROR
    status = "completed" if success else "failed"

    message = f"Operation {operation} {status}"
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message}: {context_str}"

    logger.log(level, message, extra=context)


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: Exception,
    **context
) -> None:
    """
    Log an exception with full context.

    Args:
        logger: Logger instance to use.
        message: Description of what was happening when exception occurred.
        exc: The exception that was raised.
        **context: Additional context to include in the log.

    Example:
        try:
            process_file(data)
        except Exception as e:
            log_exception(logger, "Failed to process file", e, file_name="data.xlsx")
    """
    logger.error(
        f"{message}: {exc.__class__.__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            **context,
        }
    )


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user_id: Optional[int] = None,
    **context
) -> None:
    """
    Log an incoming request.

    Args:
        logger: Logger instance to use.
        method: HTTP method (GET, POST, etc.).
        path: Request path.
        user_id: Authenticated user ID if available.
        **context: Additional context to include.
    """
    message = f"Request: {method} {path}"
    if user_id:
        message = f"{message} (user_id={user_id})"

    logger.info(message, extra={"user_id": user_id, "path": path, "method": method, **context})


def log_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **context
) -> None:
    """
    Log an outgoing response.

    Args:
        logger: Logger instance to use.
        method: HTTP method.
        path: Request path.
        status_code: Response status code.
        duration_ms: Request duration in milliseconds.
        **context: Additional context to include.
    """
    level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR

    logger.log(
        level,
        f"Response: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
        extra={
            "path": path,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **context,
        }
    )


# Convenience exports for common loggers
app_logger = get_logger("app")
controller_logger = get_logger("app.controller")
auth_logger = get_logger("app.auth")
reconciler_logger = get_logger("app.reconciler")
upload_logger = get_logger("app.upload")
