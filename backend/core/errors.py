"""
Standardized error handlers and exception mappings for the FastAPI application.

Ensures:
1. OperationalError / DB connection errors (e.g. SSL connection closed unexpectedly) return HTTP 503 instead of 500.
2. IntegrityError (unique/foreign key constraints) returns HTTP 409 instead of 500.
3. AIProviderError returns HTTP 503 instead of 500.
4. RequestValidationError returns HTTP 422 with structured detail.
5. Standard HTTPException preserves detail and status code.
6. Unhandled Exception returns a sanitized HTTP 500 without leaking stack traces or credentials.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import OperationalError, DBAPIError, IntegrityError, SQLAlchemyError

from services.ai.ai_services import AIProviderError
from utils.logger import logger


def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error(f"Database operational error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Database connection error. Please try again later.",
            "error_code": "DATABASE_UNAVAILABLE",
        },
    )


def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(f"Database integrity constraint violation on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": "Data integrity violation or duplicate record.",
            "error_code": "INTEGRITY_ERROR",
        },
    )


def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "A database error occurred. Please try again later.",
            "error_code": "DATABASE_ERROR",
        },
    )


def ai_provider_error_handler(request: Request, exc: AIProviderError) -> JSONResponse:
    logger.error(f"AI provider exhaustion on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "AI service is currently unavailable. Please try again later.",
            "error_code": "AI_SERVICE_UNAVAILABLE",
        },
    )


def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR",
        },
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
        headers=getattr(exc, "headers", None),
    )


def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


def setup_error_handlers(app: FastAPI) -> None:
    """Registers all standardized exception handlers on the FastAPI application."""
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(DBAPIError, operational_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(AIProviderError, ai_provider_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
