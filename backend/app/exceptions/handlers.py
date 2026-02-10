"""
Exception Handlers Module.

Centralized exception handling with proper logging and error responses.
Provides consistent error format across the API.
"""
import logging
import traceback
import uuid
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from .exceptions import MainException

logger = logging.getLogger("app.exceptions")


def _get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request state or generate one."""
    try:
        if hasattr(request.state, "correlation_id"):
            return request.state.correlation_id
    except Exception:
        pass
    return str(uuid.uuid4())[:8]


def _build_error_response(
    error_type: str,
    message: str,
    status_code: int,
    correlation_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build standardized error response.

    Args:
        error_type: Type/class name of the error.
        message: Human-readable error message.
        status_code: HTTP status code.
        correlation_id: Request correlation ID for tracing.
        details: Additional error details (optional).

    Returns:
        Error response dictionary.
    """
    response = {
        "error": error_type,
        "message": message,
        "status_code": status_code,
    }

    if correlation_id:
        response["correlation_id"] = correlation_id

    if details:
        response["details"] = details

    return response


def main_exception_handler(request: Request, exc: MainException) -> JSONResponse:
    """
    Handle application-specific exceptions (MainException and subclasses).

    These are expected errors from business logic validation, authentication,
    file processing, etc.

    Args:
        request: The incoming request.
        exc: The MainException instance.

    Returns:
        JSON response with error details.
    """
    correlation_id = _get_correlation_id(request)

    # Log at appropriate level based on status code
    if exc.status_code >= 500:
        logger.error(
            f"Application error: {exc.__class__.__name__} - {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "error_type": exc.__class__.__name__,
            }
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"Client error: {exc.__class__.__name__} - {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "error_type": exc.__class__.__name__,
            }
        )
    else:
        logger.info(
            f"Handled exception: {exc.__class__.__name__} - {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
            }
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            error_type=exc.__class__.__name__,
            message=exc.message,
            status_code=exc.status_code,
            correlation_id=correlation_id,
        )
    )


def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.

    This is the catch-all handler for unexpected errors. In production,
    this should hide internal error details to prevent information leakage.

    Args:
        request: The incoming request.
        exc: The unhandled exception.

    Returns:
        JSON response with generic error message.
    """
    correlation_id = _get_correlation_id(request)

    # Always log unexpected exceptions at ERROR level with full traceback
    logger.error(
        f"Unhandled exception: {exc.__class__.__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
            "error_type": exc.__class__.__name__,
        }
    )

    # Check environment for detailed error messages
    try:
        from app.config.settings import settings
        is_production = settings.is_production
    except Exception:
        is_production = True  # Default to safe mode

    # In production, hide internal error details
    if is_production:
        message = "An unexpected error occurred. Please try again later."
        details = None
    else:
        # In development, include more details for debugging
        message = str(exc)
        details = {
            "exception_type": exc.__class__.__name__,
            "traceback": traceback.format_exc().split("\n")[-5:],  # Last 5 lines
        }

    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            error_type="InternalServerError",
            message=message,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            correlation_id=correlation_id,
            details=details,
        )
    )


def _make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable types.

    Args:
        obj: Any object to convert.

    Returns:
        JSON-serializable version of the object.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, Exception):
        return str(obj)
    else:
        # Convert any other type to string
        return str(obj)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Provides detailed validation error information in a consistent format.

    Args:
        request: The incoming request.
        exc: The validation exception (RequestValidationError).

    Returns:
        JSON response with validation error details.
    """
    correlation_id = _get_correlation_id(request)

    # Get validation errors
    try:
        errors = exc.errors()  # type: ignore
    except AttributeError:
        errors = [{"msg": str(exc)}]

    # Ensure all error objects are JSON serializable
    serializable_errors = _make_json_serializable(errors)

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "errors": serializable_errors,
        }
    )

    return JSONResponse(
        status_code=422,
        content=_build_error_response(
            error_type="ValidationError",
            message="Request validation failed",
            status_code=422,
            correlation_id=correlation_id,
            details={"errors": serializable_errors},
        )
    )
