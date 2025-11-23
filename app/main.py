import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from app.customLogging.RequestLogger import RequestLoggingMiddleware
from app.database.mysql_configs import Base, engine
import logging.config
from app.customLogging.config import LOGGING
from app.exceptions.exceptions import MainException
from app.exceptions.handlers import main_exception_handler, global_exception_handler
from app.controller import reconcile, reports, upload, session

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reconciler application")
app.include_router(session.router)
app.include_router(upload.router)
app.include_router(reconcile.router)
app.include_router(reports.router)

Base.metadata.create_all(engine)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(MainException, main_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)

