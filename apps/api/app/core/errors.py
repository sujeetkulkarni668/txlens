"""Structured error responses (product spec section 26).

Two goals: (1) every error the API returns has the same predictable
shape, whether it's a validation error, an explicit HTTPException, or an
unexpected exception; (2) unexpected exceptions never leak internals
(stack traces, exception messages that might contain secrets/internal
paths) to the client — they're logged server-side with full detail and
returned to the client as a generic message plus a request-correlatable
error id.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _error_body(*, error_id: str, message: str, detail=None) -> dict:
    body = {"error_id": error_id, "message": message}
    if detail is not None:
        body["detail"] = detail
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(error_id=error_id, message="request validation failed", detail=exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        error_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(error_id=error_id, message=str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())
        # Full detail server-side only — never in the response body.
        logger.exception("unhandled exception (error_id=%s)", error_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                error_id=error_id,
                message="an unexpected error occurred; reference error_id when reporting this",
            ),
        )
