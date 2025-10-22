from fastapi import Request
from fastapi.responses import  JSONResponse
from .exceptions import MainException

def main_exception_handler(request: Request, exc: MainException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "message": exc.message}
    )


def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "message": str(exc)}
    )