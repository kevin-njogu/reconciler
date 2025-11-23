import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Read request body (must do this before calling call_next)
        body = await request.body()

        logger.info(
            f"REQUEST: {request.method} {request.url.path} "
            f"Query={dict(request.query_params)} "
            # f"Body={body.decode('utf-8') if body else None} "
            f"Headers={dict(request.headers)}"
        )

        response: Response = await call_next(request)

        duration = round(time.time() - start_time, 4)

        logger.info(
            f"RESPONSE: {request.method} {request.url.path} "
            f"Status={response.status_code} "
            f"Duration={duration}s"
        )

        return response
