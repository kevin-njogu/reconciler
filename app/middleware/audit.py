"""
Audit Logging Middleware.

Captures all POST, PUT, PATCH, DELETE operations for security auditing.
Stores audit records in the database for compliance and tracking.
"""
import logging
from typing import Callable, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.database.mysql_configs import SessionLocal
from app.auth.security import decode_token

logger = logging.getLogger("app.middleware.audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all state-changing HTTP operations.

    Logs POST, PUT, PATCH, DELETE requests with user context.
    Stores audit logs in the database for compliance tracking.
    """

    # Methods to audit
    AUDIT_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to exclude from audit (high-volume or sensitive)
    EXCLUDE_PATHS: Set[str] = {
        "/api/v1/auth/login",  # Already logged in auth controller
        "/api/v1/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log if it's a state-changing operation.

        Args:
            request: The incoming request.
            call_next: Next middleware/handler.

        Returns:
            The response from the next handler.
        """
        # Skip non-audit methods
        if request.method not in self.AUDIT_METHODS:
            return await call_next(request)

        # Skip excluded paths
        path = request.url.path
        if path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Get user ID from token if available
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload and payload.get("type") == "access":
                    user_id = payload.get("sub")
                    if user_id:
                        user_id = int(user_id)
            except Exception as e:
                # Token decode failed - log at debug level, continue without user_id
                logger.debug(f"Failed to decode token for audit: {e}")

        # Call the next handler
        response = await call_next(request)

        # Only log successful operations (2xx status codes)
        if 200 <= response.status_code < 300:
            self._log_operation(
                request=request,
                user_id=user_id,
                status_code=response.status_code
            )

        return response

    def _log_operation(
        self,
        request: Request,
        user_id: int = None,
        status_code: int = None
    ):
        """
        Create an audit log entry for the operation.

        Args:
            request: The HTTP request.
            user_id: The authenticated user's ID (if available).
            status_code: The response status code.
        """
        # Import here to avoid circular imports
        from app.sqlModels.authEntities import AuditLog

        # Determine action and resource from path
        path = request.url.path
        method = request.method

        # Parse resource type and ID from path
        # e.g., /api/v1/users/123 -> resource_type="users", resource_id="123"
        path_parts = path.strip("/").split("/")
        resource_type = None
        resource_id = None

        if len(path_parts) >= 3:
            # Skip 'api' and 'v1'
            if path_parts[0] == "api" and path_parts[1].startswith("v"):
                resource_type = path_parts[2] if len(path_parts) > 2 else None
                resource_id = path_parts[3] if len(path_parts) > 3 else None

        # Create action string
        action_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "partial_update",
            "DELETE": "delete",
        }
        action = action_map.get(method, method.lower())

        # Add resource context to action
        if resource_type:
            action = f"{action}_{resource_type}"

        # Get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", "-")

        db = None
        try:
            db = SessionLocal()
            audit = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details={
                    "status_code": status_code,
                    "query_params": dict(request.query_params),
                    "correlation_id": correlation_id,
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_path=path,
                request_method=method,
            )
            db.add(audit)
            db.commit()

            logger.debug(
                f"Audit logged: {action} by user_id={user_id}",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "path": path,
                }
            )
        except Exception as e:
            # Don't let audit logging failures affect the request
            # But log the error for investigation
            logger.error(
                f"Failed to create audit log: {e}",
                exc_info=True,
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "action": action,
                    "path": path,
                }
            )
        finally:
            if db:
                db.close()
