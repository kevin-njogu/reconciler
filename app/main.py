from fastapi import FastAPI, UploadFile, File
from .fileupload import uploadfile
from app.equity.controller import equity_controller

app = FastAPI()

app.include_router(uploadfile.router)
app.include_router(equity_controller.router)
