"""
Security Middleware.

Implements security headers and rate limiting for the application.
Critical for protecting against common web vulnerabilities.
"""
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("app.middleware.security")

# =============================================================================
# Rate Limiter Configuration
# =============================================================================

def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Checks X-Forwarded-For header for proxy scenarios,
    falls back to direct client IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create rate limiter instance
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200/minute"],  # Default for all endpoints
    storage_uri="memory://",  # In-memory storage (use Redis for distributed)
    strategy="fixed-window",
)

# Rate limit configurations for specific endpoints
RATE_LIMITS = {
    "login": "5/minute",           # Strict limit on login attempts
    "forgot_password": "3/minute", # Forgot password requests
    "reset_password": "3/minute",  # Password reset attempts
    "refresh": "10/minute",        # Moderate limit on token refresh
    "upload": "30/minute",         # Reasonable limit for file uploads
    "reconcile": "10/minute",      # Limit reconciliation runs
    "default": "100/minute",       # Default for other endpoints
}


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with details about the limit.
    """
    from starlette.responses import JSONResponse

    logger.warning(
        f"Rate limit exceeded",
        extra={
            "client_ip": get_client_ip(request),
            "path": request.url.path,
            "method": request.method,
            "limit": str(exc.detail),
        }
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Too Many Requests",
            "detail": f"Rate limit exceeded. {exc.detail}",
            "retry_after": "Please wait before making more requests.",
        },
        headers={"Retry-After": "60"},
    )


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Implements OWASP recommended security headers to protect against:
    - XSS attacks (X-XSS-Protection, Content-Security-Policy)
    - Clickjacking (X-Frame-Options)
    - MIME type sniffing (X-Content-Type-Options)
    - Information disclosure (X-Powered-By removal)
    """

    # Paths that serve API documentation (Swagger UI, ReDoc)
    _DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}

    # Base security headers (without CSP, which is environment-dependent)
    _BASE_HEADERS = {
        "X-XSS-Protection": "1; mode=block",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        "Pragma": "no-cache",
    }

    # Strict CSP for production and non-docs paths
    _STRICT_CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Relaxed CSP for API docs pages (Swagger UI / ReDoc load from CDN)
    _DOCS_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # HSTS header (only add in production with HTTPS)
    HSTS_HEADER = "max-age=31536000; includeSubDomains"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Add security headers to the response.

        Args:
            request: The incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with security headers added.
        """
        response = await call_next(request)

        # Add base security headers
        for header, value in self._BASE_HEADERS.items():
            response.headers[header] = value

        # Use relaxed CSP for docs paths (docs are disabled in production)
        if request.url.path in self._DOCS_PATHS:
            response.headers["Content-Security-Policy"] = self._DOCS_CSP
        else:
            response.headers["Content-Security-Policy"] = self._STRICT_CSP

        # Add HSTS only for HTTPS requests (check via X-Forwarded-Proto or scheme)
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = self.HSTS_HEADER

        # Remove server identification headers (if present)
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response


# =============================================================================
# File Size Validation Constants
# =============================================================================

# Maximum file size in bytes (50MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_FILE_SIZE_MB = 50


def validate_file_size(file_size: int) -> None:
    """
    Validate that file size is within acceptable limits.

    Args:
        file_size: Size of the file in bytes.

    Raises:
        ValueError: If file exceeds maximum size.
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
            f"maximum allowed size ({MAX_FILE_SIZE_MB}MB)"
        )
