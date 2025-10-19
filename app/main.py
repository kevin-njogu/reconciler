import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from app.database.mysql_configs import Base, engine
import logging.config
from app.logging.config import LOGGING
from app.exceptions.exceptions import MainException
from app.exceptions.handlers import main_exception_handler, global_exception_handler

from app.recon_session import controllers as session_controllers
from app.fileupload import controllers as file_upload_controllers
from app.gateways.equity import controllers as equity_controller
from app.gateways.mpesa import controllers as mpesa_controllers
from app.gateways.kcb import controllers as kcb_controllers


logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


app = FastAPI(title="Reconciler application")
app.include_router(session_controllers.router)
app.include_router(file_upload_controllers.router)
app.include_router(equity_controller.router)
app.include_router(mpesa_controllers.router)
app.include_router(kcb_controllers.router)

Base.metadata.create_all(engine)

app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(MainException, main_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)

