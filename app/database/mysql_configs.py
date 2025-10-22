import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

#load environment variables from .env file
load_dotenv()

database_username=os.getenv("DATABASE_USERNAME")
database_password=os.getenv("DATABASE_PASSWORD")
database_host=os.getenv("DATABASE_HOST")
database_port=os.getenv("DATABASE_PORT")
database_name=os.getenv("DATABASE_NAME")

#create engine
database_url = f'mysql+pymysql://{database_username}:{database_password}@{database_host}:{database_port}/{database_name}'
engine = create_engine(database_url)

#create a recon_session
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

#create the base class
Base = declarative_base()

#create a get db function
def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




