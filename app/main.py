import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from app.database.mysql_configs import Base, engine
import logging.config
from app.customLogging.config import LOGGING
from app.exceptions.exceptions import MainException
from app.exceptions.handlers import main_exception_handler, global_exception_handler
from app.uploads_logic import controllers as uploads_controllers
from app.controller import gateway_controllers

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reconciler application")
app.include_router(uploads_controllers.router)
app.include_router(gateway_controllers.router)

Base.metadata.create_all(engine)

app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(MainException, main_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)

