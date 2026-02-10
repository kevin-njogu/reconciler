"""
Logging Configuration Module.

Provides production-ready logging configuration with:
- Environment-based log levels (DEBUG for dev, ERROR for production)
- Structured logging support (JSON format option)
- File rotation with size limits
- Correlation ID support for request tracing
- Separate log files for errors
- Configurable per-module log levels
"""
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

# Base directory for log files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class SensitiveDataFilter(logging.Filter):
    """
    Filter that masks sensitive data in log messages.

    Prevents logging of passwords, tokens, and other sensitive information.
    """

    SENSITIVE_KEYS = {
        "password", "passwd", "pwd", "secret", "token", "api_key",
        "apikey", "access_token", "refresh_token", "authorization",
        "auth", "credential", "private_key", "secret_key"
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data in log records."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for key in self.SENSITIVE_KEYS:
                if key in msg_lower:
                    # Mask the value - simple approach
                    record.msg = self._mask_sensitive(record.msg)
                    break
        return True

    def _mask_sensitive(self, msg: str) -> str:
        """Mask sensitive values in message."""
        # This is a simple implementation - could be enhanced
        for key in self.SENSITIVE_KEYS:
            if key in msg.lower():
                # Replace potential values after common separators
                import re
                pattern = rf'({key}["\'\s:=]+)[^\s,}}\]"\']+(\s|,|}}|\]|"|\'|$)'
                msg = re.sub(pattern, r'\1***MASKED***\2', msg, flags=re.IGNORECASE)
        return msg


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Outputs logs in JSON format for better parsing by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json

        log_data = {
            "timestamp": datetime.now(ZoneInfo("Africa/Nairobi")).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "correlation_id"
            }:
                try:
                    # Only add JSON-serializable values
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data)


def get_logging_config(
    log_level: str = "INFO",
    log_format: str = "text",
    log_file_enabled: bool = True,
    log_file_path: str = "logs/app.log",
    log_file_max_bytes: int = 10 * 1024 * 1024,
    log_file_backup_count: int = 5,
    log_sql_queries: bool = False,
) -> Dict[str, Any]:
    """
    Generate logging configuration dictionary.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Log format type ("text" or "json").
        log_file_enabled: Whether to enable file logging.
        log_file_path: Path to main log file.
        log_file_max_bytes: Max size before rotation.
        log_file_backup_count: Number of backup files to keep.
        log_sql_queries: Whether to log SQL queries.

    Returns:
        Logging configuration dictionary for logging.config.dictConfig().
    """
    # Ensure absolute path for log file
    if not os.path.isabs(log_file_path):
        log_file_path = os.path.join(BASE_DIR, log_file_path)

    # Ensure log directory exists
    log_file_dir = os.path.dirname(log_file_path)
    os.makedirs(log_file_dir, exist_ok=True)

    # Error log file path
    error_log_path = log_file_path.replace(".log", ".error.log")

    # Formatters based on format type
    if log_format == "json":
        formatter_class = "app.customLogging.config.JsonFormatter"
        text_format = None
    else:
        formatter_class = "logging.Formatter"
        text_format = "%(asctime)s [%(correlation_id)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s"

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": "asgi_correlation_id.CorrelationIdFilter",
                "uuid_length": 32,
                "default_value": "-",
            },
            "sensitive_data": {
                "()": "app.customLogging.config.SensitiveDataFilter",
            },
        },
        "formatters": {
            "standard": {
                "()": formatter_class,
                **({"format": text_format, "datefmt": "%Y-%m-%d %H:%M:%S"} if text_format else {}),
            },
            "detailed": {
                "format": "%(asctime)s [%(correlation_id)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)-8s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "filters": ["correlation_id", "sensitive_data"],
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.controller": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.reconciler": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.upload": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.auth": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Third-party loggers - reduce noise
            "uvicorn": {
                "level": "INFO" if log_level == "DEBUG" else log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "WARNING",  # Reduce access log noise
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "INFO" if log_sql_queries else "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpcore": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    # Add file handlers if enabled
    if log_file_enabled:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "filters": ["correlation_id", "sensitive_data"],
            "formatter": "standard",
            "filename": log_file_path,
            "maxBytes": log_file_max_bytes,
            "backupCount": log_file_backup_count,
            "encoding": "utf-8",
        }
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "filters": ["correlation_id", "sensitive_data"],
            "formatter": "detailed",
            "filename": error_log_path,
            "maxBytes": log_file_max_bytes,
            "backupCount": log_file_backup_count,
            "encoding": "utf-8",
        }

        # Add file handlers to loggers
        for logger_name in ["app", "app.controller", "app.reconciler", "app.upload", "app.auth"]:
            config["loggers"][logger_name]["handlers"].extend(["file", "error_file"])

        config["root"]["handlers"].extend(["file", "error_file"])

    return config


def setup_logging() -> None:
    """
    Initialize logging configuration.

    Should be called once at application startup.
    """
    from app.config.settings import settings

    config = get_logging_config(
        log_level=settings.effective_log_level,
        log_format=settings.LOG_FORMAT,
        log_file_enabled=settings.LOG_FILE_ENABLED,
        log_file_path=settings.LOG_FILE_PATH,
        log_file_max_bytes=settings.LOG_FILE_MAX_BYTES,
        log_file_backup_count=settings.LOG_FILE_BACKUP_COUNT,
        log_sql_queries=settings.LOG_SQL_QUERIES,
    )

    logging.config.dictConfig(config)

    # Log startup information
    logger = logging.getLogger("app")
    logger.info(
        f"Logging initialized: level={settings.effective_log_level}, "
        f"format={settings.LOG_FORMAT}, environment={settings.ENVIRONMENT}"
    )


# Legacy support - keep LOGGING dict for backwards compatibility
LOGGING = get_logging_config()
