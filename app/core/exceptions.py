from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AFIPException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)

async def afip_exception_handler(request: Request, exc: AFIPException):
    logger.error(f"AFIP Business Error: Code {exc.code} - {exc.message}")
    status_code = 500 if exc.code >= 500 else 400
    return JSONResponse(
        status_code=status_code,
        content={"error": "AFIP Business Error", "code": exc.code, "message": exc.message},
    )

async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Internal Server Error")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "message": str(exc)},
    )
