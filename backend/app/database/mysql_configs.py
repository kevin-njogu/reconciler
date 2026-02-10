"""
Database configuration with connection pooling and production-ready settings.
"""
import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

logger = logging.getLogger("app.database")


def _get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "Database URL not configured. Set the DATABASE_URL environment variable."
        )
    return url


database_url = _get_database_url()

engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_timeout=30,
    connect_args={"connect_timeout": 10},
)


@event.listens_for(engine, "connect")
def _set_session_defaults(dbapi_connection, connection_record):
    """Set session timeouts and timezone on new connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET SESSION wait_timeout=28800")
    cursor.execute("SET SESSION interactive_timeout=28800")
    cursor.execute("SET SESSION time_zone='+03:00'")
    cursor.close()


SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def dispose_engine():
    """Dispose of the engine connection pool. Call on shutdown."""
    engine.dispose()
    logger.info("Database connection pool disposed")
