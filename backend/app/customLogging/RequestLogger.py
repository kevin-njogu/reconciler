"""
Request Logging Middleware.

Logs all incoming HTTP requests and outgoing responses with timing information.
Integrates with correlation ID for request tracing.
"""
import logging
import time
from typing import Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests and responses.

    Features:
    - Request logging with method, path, and query params
    - Response logging with status code and duration
    - Configurable path exclusions
    - Header filtering (excludes sensitive headers)
    """

    # Paths to exclude from logging (high-volume or noisy)
    EXCLUDE_PATHS: Set[str] = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }

    # Headers to exclude from logging (sensitive data)
    SENSITIVE_HEADERS: Set[str] = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
    }

    def _should_log(self, path: str) -> bool:
        """Check if request should be logged."""
        return path not in self.EXCLUDE_PATHS

    def _get_safe_headers(self, headers: dict) -> dict:
        """Get headers with sensitive values masked."""
        return {
            k: "***MASKED***" if k.lower() in self.SENSITIVE_HEADERS else v
            for k, v in headers.items()
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and log request/response details.

        Args:
            request: The incoming request.
            call_next: Next handler in the chain.

        Returns:
            The response from the next handler.
        """
        path = request.url.path

        # Skip logging for excluded paths
        if not self._should_log(path):
            return await call_next(request)

        start_time = time.perf_counter()

        # Get correlation ID if available
        correlation_id = request.headers.get("X-Correlation-ID", "-")

        # Log request
        logger.info(
            f"Request: {request.method} {path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        # Debug level: include headers (with sensitive data masked)
        if logger.isEnabledFor(logging.DEBUG):
            safe_headers = self._get_safe_headers(dict(request.headers))
            logger.debug(
                f"Request headers: {safe_headers}",
                extra={"correlation_id": correlation_id}
            )

        # Process request
        try:
            response: Response = await call_next(request)
        except Exception as e:
            # Log exception and re-raise
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {path} - {e.__class__.__name__}: {str(e)}",
                exc_info=True,
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log response
        logger.log(
            log_level,
            f"Response: {request.method} {path} -> {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )

        return response
