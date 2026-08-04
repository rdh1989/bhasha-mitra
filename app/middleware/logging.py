"""
Request logging middleware.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("bhasha_mitra")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request.
    """

    async def dispatch(self, request: Request, call_next):

        logger.info(
            "%s %s",
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        logger.info(
            "%s -> %s",
            request.url.path,
            response.status_code,
        )

        return response