from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.auth import (
    JOB_TRIGGER_ROLES,
    ROLE_ADMIN,
    ROLES,
    SESSION_ROLE_KEY,
    SESSION_USER_KEY,
    authenticate,
    current_user,
    is_logged_in,
    require_api_role,
    require_login_page,
    require_role_page,
)
from app.config import APP_BUILD, APP_NAME, APP_VERSION
from app.user_mgmt import recovery, repository, service
from app.user_mgmt.recovery_questions import RECOVERY_QUESTIONS

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _metadata() -> dict:
    return {"app_name": APP_NAME, "app_version": APP_VERSION, "app_build": APP_BUILD}


def _public_user(row) -> dict:
    data = dict(row)
    for key in tuple(data):
        if key == "password_hash" or key.startswith("recovery_answer_hash") or key.startswith("recovery_reset_"):
            data.pop(key, None)
    return data


def _page_context(request: Request, **extra) -> dict:
    user = current_user(request)
    return {
        **_metadata(),
        "current_user": user,
        "can_trigger_jobs": user and user["role"] in JOB_TRIGGER_ROLES,
        "is_admin": user and user["role"] == ROLE_ADMIN,
        **extra,
    }


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {**_metadata(), "error": None, "success": request.query_params.get("message")}
    )


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    client_host = request.client.host if request.client else "unknown"
    user = authenticate(username, password)
    if user is not None:
        request.session[SESSION_USER_KEY] = user["username"]
        request.session[SESSION_ROLE_KEY] = user["role"]
        logger.info("Login succeeded for user '%s' (role=%s) from %s", username, user["role"], client_host)
        return RedirectResponse(url="/dashboard", status_code=303)
    logger.warning("Login failed for user '%s' from %s", username, client_host)
    return templates.TemplateResponse(
        request, "login.html", {**_metadata(), "error": "Invalid username or password", "success": None}, status_code=401
    )


@router.get("/logout")
def logout(request: Request):
    logger.info("User '%s' logged out", request.session.get(SESSION_USER_KEY))
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request, "signup.html", {**_metadata(), "error": None, "recovery_questions": RECOVERY_QUESTIONS})


@router.post("/signup")
def signup_submit(
    request: Request,
    username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
    question_1: str = Form(...), answer_1: str = Form(...), question_2: str = Form(...), answer_2: str = Form(...),
    question_3: str = Form(...), answer_3: str = Form(...),
):
    try:
        service.create_public_user(
            username, password, confirm_password,
            (question_1, question_2, question_3), (answer_1, answer_2, answer_3),
        )
    except (ValueError, db.sqlite3.IntegrityError) as exc:
        message = "That username is already in use." if isinstance(exc, db.sqlite3.IntegrityError) else str(exc)
        return templates.TemplateResponse(request, "signup.html", {**_metadata(), "error": message, "recovery_questions": RECOVERY_QUESTIONS}, status_code=400)
    return RedirectResponse(url="/login?message=Account+created.+Please+sign+in.", status_code=303)


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    recovery.clear(request.session)
    return templates.TemplateResponse(request, "forgot_password.html", {**_metadata(), "error": None, "questions": None})


@router.post("/forgot-password")
def forgot_password_start(request: Request, username: str = Form(...)):
    result = recovery.begin(username, request.session)
    if result is None:
        return templates.TemplateResponse(
            request, "forgot_password.html", {**_metadata(), "error": None, "questions": None,
            "message": "If this account is eligible for recovery, continue with the recovery process."},
        )
    _username, questions = result
    return templates.TemplateResponse(
        request, "forgot_password.html", {**_metadata(), "error": None, "questions": questions},
    )


@router.post("/forgot-password/verify")
def forgot_password_verify(
    request: Request,
    answer_1: str = Form(...), answer_2: str = Form(...), answer_3: str = Form(...),
):
    if not recovery.verify((answer_1, answer_2, answer_3), request.session):
        return templates.TemplateResponse(
            request, "forgot_password.html", {**_metadata(), "error": "Recovery verification failed.", "questions": None}, status_code=400,
        )
    return RedirectResponse(url="/forgot-password/reset", status_code=303)


@router.get("/forgot-password/reset", response_class=HTMLResponse)
def forgot_password_reset_page(request: Request):
    if not request.session.get(recovery.SESSION_TOKEN):
        return RedirectResponse(url="/forgot-password", status_code=303)
    return templates.TemplateResponse(request, "forgot_password_reset.html", {**_metadata(), "error": None})


@router.post("/forgot-password/reset")
def forgot_password_reset(request: Request, new_password: str = Form(...), confirm_password: str = Form(...)):
    try:
        recovery.complete(new_password, confirm_password, request.session)
    except ValueError as exc:
        return templates.TemplateResponse(request, "forgot_password_reset.html", {**_metadata(), "error": str(exc)}, status_code=400)
    return RedirectResponse(url="/login?message=Password+reset+successfully.", status_code=303)


@router.get("/account/security", response_class=HTMLResponse)
def security_page(request: Request):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    user = repository.get_user_by_username(current_user(request)["username"])
    return templates.TemplateResponse(
        request, "security.html", _page_context(request, user=user, recovery_questions=RECOVERY_QUESTIONS, error=None, success=None),
    )


@router.post("/account/security/recovery")
def security_recovery(
    request: Request,
    current_password: str = Form(...), question_1: str = Form(...), answer_1: str = Form(...),
    question_2: str = Form(...), answer_2: str = Form(...), question_3: str = Form(...), answer_3: str = Form(...),
):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    user = repository.get_user_by_username(current_user(request)["username"])
    try:
        service.configure_recovery(
            user["id"], current_password, (question_1, question_2, question_3), (answer_1, answer_2, answer_3),
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request, "security.html", _page_context(request, user=user, recovery_questions=RECOVERY_QUESTIONS, error=str(exc), success=None), status_code=400,
        )
    user = repository.get_user(user["id"])
    return templates.TemplateResponse(
        request, "security.html", _page_context(request, user=user, recovery_questions=RECOVERY_QUESTIONS, error=None, success="Recovery questions saved."),
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    redirect = require_role_page(request, ROLE_ADMIN)
    if redirect:
        return redirect
    users = [_public_user(row) for row in db.list_users()]
    return templates.TemplateResponse(request, "users.html", _page_context(request, users=users, roles=ROLES))


def _ensure_not_last_admin(user_row, demoting: bool = False, deactivating: bool = False, deleting: bool = False) -> None:
    if user_row["role"] == ROLE_ADMIN and (demoting or deactivating or deleting) and db.count_admins(exclude_id=user_row["id"]) == 0:
        raise HTTPException(status_code=400, detail="Cannot remove the last remaining admin account.")


@router.get("/api/users")
def api_list_users(request: Request):
    require_api_role(request, ROLE_ADMIN)
    return {"items": [_public_user(row) for row in db.list_users()]}


@router.post("/api/users")
def api_create_user(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...)):
    require_api_role(request, ROLE_ADMIN)
    username = username.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if db.get_user_by_username(username) is not None:
        raise HTTPException(status_code=409, detail=f"User '{username}' already exists.")
    user = db.create_user(username, password, role)
    logger.info("User '%s' (role=%s) created by admin '%s'", username, role, request.session.get(SESSION_USER_KEY))
    return _public_user(user)


@router.put("/api/users/{user_id}")
def api_update_user(request: Request, user_id: int, role: str | None = Form(None), is_active: bool | None = Form(None), password: str | None = Form(None)):
    require_api_role(request, ROLE_ADMIN)
    row = db.get_user_by_id(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    if role is not None and role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    _ensure_not_last_admin(row, demoting=(role is not None and role != ROLE_ADMIN), deactivating=(is_active is False))
    db.update_user(user_id, role=role, is_active=is_active, password=password or None)
    logger.info("User '%s' updated by admin '%s'", row["username"], request.session.get(SESSION_USER_KEY))
    return _public_user(db.get_user_by_id(user_id))


@router.delete("/api/users/{user_id}")
def api_delete_user(request: Request, user_id: int):
    actor = require_api_role(request, ROLE_ADMIN)
    row = db.get_user_by_id(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    if row["username"] == actor["username"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account while logged in.")
    _ensure_not_last_admin(row, deleting=True)
    db.delete_user(user_id)
    logger.info("User '%s' deleted by admin '%s'", row["username"], actor["username"])
    return {"ok": True}
