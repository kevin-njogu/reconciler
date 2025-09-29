from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


URL_DATABASE_TEST='mysql+pymysql://root:root@127.0.0.1:3306/reconciler'
URL_DATABASE_LIVE=""

engine = create_engine(URL_DATABASE_TEST)
session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

