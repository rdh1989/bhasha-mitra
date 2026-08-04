"""
Global exception middleware.

Intercepts all unhandled exceptions and converts them into a
standardized API error response.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.exceptions.application_exception import ApplicationException

logger = logging.getLogger(__name__)


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware responsible for handling all application exceptions.
    """

    async def dispatch(self, request: Request, call_next):

        try:
            return await call_next(request)

        #
        # Application Exceptions
        #
        except ApplicationException as exc:

            logger.warning(
                "%s | %s | %s",
                exc.error_code,
                request.url.path,
                exc.message,
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=self._error_response(
                    request=request,
                    code=exc.error_code,
                    message=exc.message,
                    details=exc.details,
                ),
            )

        #
        # Request Validation (422)
        #
        except RequestValidationError as exc:

            logger.warning(
                "VALIDATION_ERROR | %s",
                request.url.path,
            )

            return JSONResponse(
                status_code=422,
                content=self._error_response(
                    request=request,
                    code="VALIDATION_ERROR",
                    message="Request validation failed.",
                    details=exc.errors(),
                ),
            )

        #
        # HTTP Exceptions (404, 405, etc.)
        #
        except StarletteHTTPException as exc:

            logger.warning(
                "HTTP_%s | %s",
                exc.status_code,
                request.url.path,
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=self._error_response(
                    request=request,
                    code=f"HTTP_{exc.status_code}",
                    message=str(exc.detail),
                ),
            )

        #
        # Unexpected Errors (500)
        #
        except Exception:

            logger.exception(
                "Unhandled exception while processing %s",
                request.url.path,
            )

            return JSONResponse(
                status_code=500,
                content=self._error_response(
                    request=request,
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected error occurred.",
                ),
            )

    @staticmethod
    def _error_response(
        *,
        request: Request,
        code: str,
        message: str,
        details: object | None = None,
    ) -> dict:

        return {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "correlation_id": getattr(
                request.state,
                "correlation_id",
                None,
            ),
        }