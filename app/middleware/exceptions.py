"""
===============================================================================
BHASHA MITRA

Module:
    exceptions.py

Layer:
    Presentation / Middleware

Description:
    Global exception handling middleware.

Responsibilities:
    - Handle unhandled application exceptions
    - Handle request validation errors safely
    - Prevent raw request bytes from being JSON-decoded
    - Return consistent API error responses
    - Preserve correlation IDs
===============================================================================
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def _sanitize_value(
    value: object,
) -> object:
    """
    Convert values that are unsafe for JSON serialization
    into safe representations.

    In particular, FastAPI validation errors may contain the
    complete raw multipart request body as bytes.
    """

    if isinstance(value, bytes):

        return value.decode(
            "utf-8",
            errors="replace",
        )

    if isinstance(value, bytearray):

        return bytes(value).decode(
            "utf-8",
            errors="replace",
        )

    if isinstance(value, dict):

        return {
            str(key): _sanitize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):

        return [
            _sanitize_value(item)
            for item in value
        ]

    return value


def _sanitize_validation_errors(
    errors: list[dict],
) -> list[dict]:
    """
    Make FastAPI validation errors JSON-safe.
    """

    return [
        _sanitize_value(error)
        for error in errors
    ]


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    Global exception middleware for Bhasha Mitra.
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        """
        Process request and handle exceptions.
        """

        correlation_id = request.headers.get(
            "X-Correlation-ID"
        )

        if not correlation_id:

            correlation_id = str(
                uuid4()
            )

        try:

            response = await call_next(
                request
            )

            response.headers[
                "X-Correlation-ID"
            ] = correlation_id

            return response

        except RequestValidationError as exc:

            errors = _sanitize_validation_errors(
                exc.errors()
            )

            logger.warning(
                "Request validation failed | "
                "path=%s | correlation_id=%s | errors=%s",
                request.url.path,
                correlation_id,
                errors,
            )

            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "detail": errors,
                    "correlation_id": correlation_id,
                },
                headers={
                    "X-Correlation-ID": correlation_id,
                },
            )

        except Exception as exc:

            logger.exception(
                "Unhandled exception | "
                "path=%s | correlation_id=%s",
                request.url.path,
                correlation_id,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "INTERNAL_SERVER_ERROR",
                    "detail": "Internal server error.",
                    "correlation_id": correlation_id,
                },
                headers={
                    "X-Correlation-ID": correlation_id,
                },
            )


def register_exception_middleware(
    app,
) -> None:
    """
    Register global exception middleware.
    """

    app.add_middleware(
        ExceptionMiddleware
    )