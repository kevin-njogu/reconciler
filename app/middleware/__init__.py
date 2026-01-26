"""
Middleware module for request processing.
"""
from app.middleware.audit import AuditLogMiddleware

__all__ = ["AuditLogMiddleware"]
