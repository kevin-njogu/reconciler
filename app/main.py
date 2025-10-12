from fastapi import FastAPI, UploadFile, File
from .fileupload import uploadfile
from app.controllers import controller

app = FastAPI()

app.include_router(uploadfile.router)
app.include_router(controller.router)

