"""
Middleware registration.

Centralized registration of all application middleware.
"""

from __future__ import annotations

from fastapi import FastAPI

from .correlation import CorrelationIdMiddleware
from .exceptions import ExceptionMiddleware
from .logging import RequestLoggingMiddleware
from .timing import RequestTimingMiddleware


def register_middlewares(app: FastAPI) -> None:
    """
    Register all middleware in the correct execution order.

    Execution Order (Request):
        CorrelationId
            ↓
        Timing
            ↓
        Logging
            ↓
        Exception
            ↓
        Route

    Response flows in reverse order.
    """

    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)