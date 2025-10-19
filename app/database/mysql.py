from contextlib import contextmanager, asynccontextmanager
import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

#load environment variables from .env file
load_dotenv()

class Base(DeclarativeBase):
    pass

#get db URL
DATABASE_URL = os.getenv("DATABASE_URL")

#Create engine
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine,autoflush=True)

#Create db connection and tables
def get_session():
    db = Session()
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise
    finally:
        db.close()

#Create db tables
def create_db_and_tables():
    Base.metadata.create_all(engine)

async def lifespan(app: FastAPI):
    print("start up ...")
    create_db_and_tables()
    yield
    print('shutting down ...')




