"""
Request timing middleware.

Measures HTTP request execution time and exposes the duration
through the X-Process-Time response header.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


PROCESS_TIME_HEADER = "X-Process-Time"


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Measures request execution time.

    The measured duration is returned in seconds through the
    X-Process-Time response header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        """
        Measure the complete request processing duration.
        """

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

        except Exception:
            # Do not handle the exception here.
            # Exception handling belongs to ExceptionMiddleware.
            raise

        finally:
            duration = (
                time.perf_counter() - start_time
            )

        response.headers[PROCESS_TIME_HEADER] = (
            f"{duration:.6f}"
        )

        return response