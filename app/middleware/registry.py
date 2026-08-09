"""
Middleware registration.

Centralized registration of all application middleware.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .authentication import AuthenticationMiddleware

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
    # Session must wrap authentication so request.session is available.
    import os

    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv(
            "BHASHA_SESSION_SECRET",
            "bhasha-mitra-dev-session-secret-change-me",
        ),
        session_cookie="bhasha_mitra_session",
        max_age=60 * 60 * 24 * 30,
        same_site="lax",
        https_only=False,
    )
