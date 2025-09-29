from contextlib import contextmanager

from fastapi import Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from .database_variables import session_local, Base, engine


@contextmanager
def get_db_session():
        Base.metadata.create_all(bind=engine)
        db = session_local()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()