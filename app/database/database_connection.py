from contextlib import contextmanager

from .database_variables import DbConfigs

Base = DbConfigs.Base
session_local = DbConfigs.session_local
engine = DbConfigs.engine

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