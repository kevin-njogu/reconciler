"""
Payment Gateway Reconciliation Application.

FastAPI application for reconciling bank statements against internal records.
Supports multiple gateways: Equity, KCB, M-Pesa, and Workpay.
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

# Initialize logging FIRST - before any other imports that might use logging
from app.customLogging import setup_logging
setup_logging()

from app.config.settings import settings
from app.auth.config import validate_auth_config
from app.customLogging.RequestLogger import RequestLoggingMiddleware
from app.middleware.audit import AuditLogMiddleware
from app.middleware.security import (
    SecurityHeadersMiddleware,
    limiter,
    rate_limit_exceeded_handler,
)
from app.database.mysql_configs import Base, engine, dispose_engine
from app.exceptions.exceptions import MainException
from app.exceptions.handlers import (
    main_exception_handler,
    global_exception_handler,
    validation_exception_handler,
)
from app.controller import (
    reconcile,
    reports,
    upload,
    runs,
    gateway_config,
    operations,
    dashboard,
    transactions,
    auth,
    users,
)

# Import models for table creation (SQLAlchemy needs these imported to create tables)
from app.sqlModels.runEntities import ReconciliationRun, UploadedFile  # noqa: F401
from app.sqlModels.transactionEntities import Transaction  # noqa: F401
from app.sqlModels.gatewayEntities import Gateway, GatewayFileConfig, GatewayChangeRequest  # noqa: F401
from app.sqlModels.authEntities import User, RefreshToken, LoginSession, AuditLog  # noqa: F401

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Handles startup and shutdown events with proper logging.
    """
    # Startup
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION}",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "log_level": settings.effective_log_level,
        }
    )

    # Validate critical configuration
    validate_auth_config()
    logger.info("Auth configuration validated successfully")

    # Create database tables
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")
    dispose_engine()


# Disable OpenAPI docs in production
_docs_url = "/docs" if not settings.is_production else None
_redoc_url = "/redoc" if not settings.is_production else None
_openapi_url = "/openapi.json" if not settings.is_production else None

app = FastAPI(
    title=settings.APP_NAME,
    description="API for reconciling external bank statements against internal payment records",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    debug=settings.DEBUG,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# Attach rate limiter to app state
app.state.limiter = limiter

# ============================================================================
# MIDDLEWARE STACK (order matters - executed in reverse order)
# ============================================================================

# Security headers middleware (adds HSTS, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware - allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Audit logging middleware (for state-changing operations)
app.add_middleware(AuditLogMiddleware)

# Correlation ID middleware (for request tracing)
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Correlation-ID",
    update_request_header=True,
)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(MainException, main_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(reconcile.router)
app.include_router(reports.router)
app.include_router(runs.router)
app.include_router(gateway_config.router)
app.include_router(operations.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns basic application health status.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.effective_log_level.lower(),
    )
