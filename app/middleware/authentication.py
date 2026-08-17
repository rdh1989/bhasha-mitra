from __future__ import annotations

import secrets
from urllib.parse import quote

from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.security import (
    INTERNAL_API_HEADER,
    INTERNAL_API_TOKEN,
    SESSION_TIMEOUT,
    SQLiteAuthRepository,
)


SESSION_COOKIE = "bhasha_mitra_session"
PUBLIC_PATHS = {"/login", "/api/v1/health"}
ADMIN_PREFIXES = ("/users", "/settings", "/logs")
OPERATOR_PAGES = {"/upload", "/translation"}
OPERATOR_API_PREFIXES = (
    "/api/v1/upload",
    "/api/v1/jobs/",
    "/api/v1/translate",
)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, repository: SQLiteAuthRepository) -> None:
        super().__init__(app)
        self._repository = repository

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/static/"):
            return await call_next(request)

        internal_token = request.headers.get(INTERNAL_API_HEADER, "")
        if internal_token and secrets.compare_digest(internal_token, INTERNAL_API_TOKEN):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        user = (
            self._repository.get_session_user(
                token,
                refresh=path == "/api/v1/session/keep-alive",
            )
            if token
            else None
        )
        if user is None:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Authentication required."}, status_code=401)
            next_path = quote(path if path.startswith("/") else "/")
            response = RedirectResponse(f"/login?next={next_path}", status_code=303)
            response.delete_cookie(SESSION_COOKIE)
            return response

        request.state.user = user

        if path.startswith(ADMIN_PREFIXES) and user.role != "admin":
            return self._forbidden(path)

        if path in OPERATOR_PAGES and user.role not in {"admin", "operator"}:
            return self._forbidden(path)

        if path == "/api/v1/upload/browse" and user.role not in {"admin", "operator"}:
            return self._forbidden(path)

        if path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if user.role == "user":
                return self._forbidden(path)
            if user.role == "operator" and not path.startswith(OPERATOR_API_PREFIXES):
                return self._forbidden(path)

        response = await call_next(request)
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=int(SESSION_TIMEOUT.total_seconds()),
            httponly=True,
            samesite="strict",
            secure=False,
        )
        return response

    @staticmethod
    def _forbidden(path: str):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Insufficient permissions."}, status_code=403)
        return RedirectResponse("/dashboard", status_code=303)