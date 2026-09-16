"""Session-cookie authentication backed by the SQLite users table, with
simple role-based access control (admin / operator / user)."""
from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app import db
from app.db import ROLE_ADMIN, ROLE_OPERATOR, ROLE_USER, ROLES

SESSION_USER_KEY = "user"
SESSION_ROLE_KEY = "role"

# Roles allowed to create/trigger translation jobs (admin can do everything an
# operator can, plus user administration; "user" is strictly read-only).
JOB_TRIGGER_ROLES = (ROLE_ADMIN, ROLE_OPERATOR)
ADMIN_ONLY_ROLES = (ROLE_ADMIN,)


def authenticate(username: str, password: str):
    """Returns the DB user row on success, else None."""
    return db.authenticate(username, password)


def current_user(request: Request) -> dict | None:
    username = request.session.get(SESSION_USER_KEY)
    role = request.session.get(SESSION_ROLE_KEY)
    if not username or not role:
        return None
    return {"username": username, "role": role}


def is_logged_in(request: Request) -> bool:
    return current_user(request) is not None


def require_login_page(request: Request) -> RedirectResponse | None:
    """For HTML routes: redirect to /login if not authenticated."""
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def require_role_page(request: Request, *roles: str) -> RedirectResponse | None:
    """For HTML routes: redirect to /login if unauthenticated, or to the
    dashboard (with an error flag) if authenticated but lacking permission."""
    redirect = require_login_page(request)
    if redirect:
        return redirect
    user = current_user(request)
    if user["role"] not in roles:
        return RedirectResponse(url="/dashboard?error=forbidden", status_code=303)
    return None


def require_api_auth(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_api_role(request: Request, *roles: str) -> dict:
    user = require_api_auth(request)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
    return user

