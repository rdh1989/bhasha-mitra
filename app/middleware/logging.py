"""
Request logging middleware.

Logs incoming HTTP requests and their corresponding responses.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger("bhasha_mitra")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming HTTP request and its response.

    The middleware records:
    - HTTP method
    - request path
    - correlation ID when available
    - response status code
    - request duration
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        """
        Process an HTTP request and log its lifecycle.
        """

        start_time = time.perf_counter()

        correlation_id = getattr(
            request.state,
            "correlation_id",
            None,
        )

        logger.info(
            "HTTP request started | "
            "method=%s path=%s correlation_id=%s",
            request.method,
            request.url.path,
            correlation_id or "-",
        )

        try:
            response = await call_next(request)

        except Exception:
            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            logger.exception(
                "HTTP request failed | "
                "method=%s path=%s "
                "duration_ms=%.2f "
                "correlation_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                correlation_id or "-",
            )

            raise

        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        logger.info(
            "HTTP request completed | "
            "method=%s path=%s "
            "status_code=%s "
            "duration_ms=%.2f "
            "correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id or "-",
        )

        return response