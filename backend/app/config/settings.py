"""
Application Settings Module.

Centralized configuration management using Pydantic Settings.
Supports environment-based configuration for development and production.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables can be set directly or via a .env file.
    """

    # Application
    APP_NAME: str = "Payment Gateway Reconciliation API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "json"
    LOG_FILE_ENABLED: bool = False
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_FILE_MAX_BYTES: int = 10485760
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_SQL_QUERIES: bool = False
    LOG_REQUEST_BODY: bool = False
    LOG_RESPONSE_BODY: bool = False

    # CORS
    CORS_ORIGINS: list[str]

    # Database
    DATABASE_URL: str

    # Storage
    STORAGE_BACKEND: Literal["local", "gcs"] = "local"
    LOCAL_UPLOADS_PATH: str = "uploads"
    GCS_BUCKET: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def effective_log_level(self) -> str:
        """
        Get effective log level based on environment.

        In production, minimum level is WARNING unless explicitly set lower.
        In development, respects LOG_LEVEL setting (defaults to DEBUG).
        """
        if self.is_production:
            # Production: minimum ERROR level for most logs
            level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
            configured_priority = level_priority.get(self.LOG_LEVEL.upper(), 3)
            return self.LOG_LEVEL.upper() if configured_priority >= 3 else "ERROR"
        return self.LOG_LEVEL.upper()

    @property
    def database_url(self) -> str:
        """Get database URL from configuration."""
        return self.DATABASE_URL


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache for performance - settings are loaded once and reused.
    """
    return Settings()


# Convenience export
settings = get_settings()
