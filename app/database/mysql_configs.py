import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()
database_url = os.getenv("DATABASE_URL_DOCKER")

engine = create_engine(database_url)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()

def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




