"""
Correlation ID middleware.

Provides a unique identifier for tracing a request across
middleware, API, application services, workers, and logs.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


CORRELATION_HEADER = "X-Correlation-ID"
MAX_CORRELATION_ID_LENGTH = 128


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Adds a correlation ID to every request.

    If the client provides an X-Correlation-ID header, the value
    is reused when it is valid. Otherwise, a new UUID is generated.

    The correlation ID is:
    - stored in request.state.correlation_id
    - returned in the X-Correlation-ID response header
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        """
        Attach a correlation ID to the current request.
        """

        correlation_id = request.headers.get(
            CORRELATION_HEADER
        )

        if not self._is_valid_correlation_id(
            correlation_id
        ):
            correlation_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id

        response = await call_next(request)

        response.headers[
            CORRELATION_HEADER
        ] = correlation_id

        return response

    @staticmethod
    def _is_valid_correlation_id(
        correlation_id: str | None,
    ) -> bool:
        """
        Validate a client-provided correlation ID.

        Correlation IDs are tracing metadata, not authentication
        credentials. We only require a non-empty value with a
        reasonable length and safe characters.
        """

        if not correlation_id:
            return False

        if len(correlation_id) > MAX_CORRELATION_ID_LENGTH:
            return False

        return all(
            character.isalnum()
            or character in "-_.:"
            for character in correlation_id
        )