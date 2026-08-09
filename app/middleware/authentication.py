"""Authentication middleware for the browser application."""

from __future__ import annotations

from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse


PUBLIC_FRONTEND_PATHS = {"/login"}
PUBLIC_API_PATHS = {"/api/v1/health"}
PUBLIC_PATH_PREFIXES = ("/static", "/docs", "/redoc")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Protect browser pages while keeping health/docs publicly reachable."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if self._is_public(path):
            return await call_next(request)

        authenticated = bool(request.session.get("user_id"))
        if authenticated:
            expires_at = request.session.get("expires_at")
            if expires_at:
                try:
                    if datetime.now(timezone.utc).timestamp() >= float(expires_at):
                        request.session.clear()
                        authenticated = False
                except (TypeError, ValueError):
                    request.session.clear()
                    authenticated = False

        if authenticated:
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        return RedirectResponse(url="/login", status_code=303)

    @staticmethod
    def _is_public(path: str) -> bool:
        return (
            path in PUBLIC_FRONTEND_PATHS
            or path in PUBLIC_API_PATHS
            or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)
        )
