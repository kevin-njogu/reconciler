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
from slowapi.middleware import SlowAPIMiddleware

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

    # Security headers to add to all responses
    SECURITY_HEADERS = {
        # Prevent XSS attacks
        "X-XSS-Protection": "1; mode=block",

        # Prevent clickjacking
        "X-Frame-Options": "DENY",

        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",

        # Referrer policy for privacy
        "Referrer-Policy": "strict-origin-when-cross-origin",

        # Permissions policy (restrict browser features)
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",

        # Cache control for sensitive data
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        "Pragma": "no-cache",
    }

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

        # Add standard security headers
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value

        # Add HSTS only for HTTPS requests (check via X-Forwarded-Proto or scheme)
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = self.HSTS_HEADER

        # Remove server identification headers
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

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
