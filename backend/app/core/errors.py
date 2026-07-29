from email import message
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.exceptions import AppError
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[Any] = []

class ErrorResponse(BaseModel):
    error: ErrorBody


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    )
    logger.warning("AppError: %s | %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    body = ErrorResponse(
        error=ErrorBody(
            code="INTERNAL_ERROR",
            message="Internal server error",
            details=[],
        )
    )
    return JSONResponse(status_code=500, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)