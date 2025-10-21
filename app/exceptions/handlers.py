from fastapi import Request
from fastapi.responses import  JSONResponse
from .exceptions import MainException

def main_exception_handler(request:Request, exc:MainException):
    return JSONResponse(
        content = {"message": f'{exc.message}'}
    )


def global_exception_handler(request:Request, exc:Exception):
    return JSONResponse(
        content = {"message": f'Internal error: {exc.__str__()}'}
    )