from fastapi import Request
from fastapi.responses import  JSONResponse
from .exceptions import MainException

def main_exception_handler(request:Request, exc:MainException):
    return JSONResponse(
        status_code= 404,
        content = {"message": f'{exc.message}'}
    )


def global_exception_handler(request:Request, exc:Exception):
    return JSONResponse(
        status_code= 500,
        content = {"message": f'Internal error: {exc.__str__()}'}
    )