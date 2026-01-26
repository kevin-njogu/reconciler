import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()


def _get_database_url() -> str:
    """Get database URL based on environment."""
    running_in_docker = os.path.exists("/.dockerenv")
    if running_in_docker:
        return os.getenv("DATABASE_URL_DOCKER")
    return os.getenv("DATABASE_URL_LOCAL", os.getenv("DATABASE_URL_DOCKER"))


database_url = _get_database_url()
engine = create_engine(database_url)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




