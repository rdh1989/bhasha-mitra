"""
===============================================================================
Bhasha Mitra
Frontend Routes

Description:
    Frontend page routing using FastAPI + Jinja2

Author  : Team 4
Version : 1.0.0
===============================================================================
"""

from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import subprocess

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import psutil

from app.middleware.authentication import SESSION_COOKIE
from app.security import ROLES, SQLiteAuthRepository
from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)

# =============================================================================
# Templates
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

# =============================================================================
# Router
# =============================================================================

router = APIRouter(
    tags=["Frontend"]
)

# =============================================================================
# Helper Functions
# =============================================================================


def template_context(request: Request, **kwargs):
    """
    Common template context.
    """

    context = {
        "request": request,
        "app_name": "Bhasha Mitra",
        "current_year": datetime.now().year,
        "current_user": getattr(request.state, "user", None),
    }

    context.update(kwargs)

    return context


def _get_application_container(
    request: Request,
) -> ApplicationContainer | None:
    return getattr(
        request.app.state,
        "application_container",
        None,
    )


def _get_auth_repository(request: Request) -> SQLiteAuthRepository:
    return request.app.state.auth_repository


def _format_dashboard_timestamp(value) -> str:
    if value is None:
        return "Just now"

    try:
        return value.strftime(
            "%d %b %Y %H:%M"
        )
    except AttributeError:
        return str(value)


def _read_gpu_usage() -> str:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        OSError,
    ):
        return "Not available"

    usages = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not usages:
        return "Not available"

    if len(usages) == 1:
        return f"{usages[0]}%"

    return ", ".join(
        f"GPU {index + 1}: {usage}%"
        for index, usage in enumerate(usages)
    )


def _build_system_information() -> dict[str, str]:
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(
        Path.cwd().anchor or "/"
    )

    return {
        "cpu_usage": f"{psutil.cpu_percent(interval=0.0):.1f}%",
        "memory_usage": f"{memory.percent:.1f}%",
        "gpu_usage": _read_gpu_usage(),
        "disk_usage": (
            f"{(disk.used / disk.total) * 100:.1f}%"
        ),
    }


def _build_dashboard_data(
    jobs,
) -> dict:
    sorted_jobs = sorted(
        jobs,
        key=lambda job: job.updated_at,
        reverse=True,
    )

    dashboard = {
        "total_videos": len(sorted_jobs),
        "completed": sum(
            1 for job in sorted_jobs
            if job.status.value == "COMPLETED"
        ),
        "processing": sum(
            1 for job in sorted_jobs
            if job.status.value in {"PENDING", "QUEUED", "RUNNING", "RETRYING"}
        ),
        "failed": sum(
            1 for job in sorted_jobs
            if job.status.value == "FAILED"
        ),
        "queued": sum(
            1 for job in sorted_jobs
            if job.status.value == "QUEUED"
        ),
    }

    recent_jobs = []

    status_classes = {
        "COMPLETED": "success",
        "FAILED": "danger",
        "CANCELLED": "danger",
        "RUNNING": "info",
        "RETRYING": "warning",
        "QUEUED": "warning",
        "PENDING": "warning",
    }

    for job in sorted_jobs[:5]:
        recent_jobs.append(
            {
                "job_id": job.id,
                "file_name": Path(job.input_file).name,
                "language_pair": (
                    f"{job.source_language or 'Auto'} → {job.target_language or '-'}"
                ),
                "status": job.status.value,
                "status_label": job.status.value.title(),
                "status_class": status_classes.get(
                    job.status.value,
                    "info",
                ),
                "progress": job.progress.percentage,
                "updated_at": _format_dashboard_timestamp(job.updated_at),
            }
        )

    return {
        "dashboard": dashboard,
        "recent_jobs": recent_jobs,
        "system_information": _build_system_information(),
    }


def render_dashboard(request: Request):
    """
    Common dashboard renderer.
    """

    container = _get_application_container(
        request
    )

    jobs = []

    if container is not None:
        jobs = container.job_service.list_all()

    view_model = _build_dashboard_data(
        jobs
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=template_context(
            request,
            page="dashboard",
            dashboard=view_model["dashboard"],
            recent_jobs=view_model["recent_jobs"],
            system_information=view_model["system_information"],
        ),
    )


# =============================================================================
# Home
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Default application page.
    """

    return render_dashboard(request)


# =============================================================================
# Dashboard
# =============================================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):

    return render_dashboard(request)


# =============================================================================
# Upload
# =============================================================================

@router.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context=template_context(
            request,
            page="upload",
        ),
    )


# =============================================================================
# Translation
# =============================================================================

@router.get("/translation", response_class=HTMLResponse)
async def translation(request: Request):

    job_id = request.query_params.get(
        "job_id"
    )

    source_language = request.query_params.get(
        "source_language"
    )

    target_language = request.query_params.get(
        "target_language"
    )

    return templates.TemplateResponse(
        request=request,
        name="translation.html",
        context=template_context(
            request,
            page="translation",
            job_id=job_id,
            source_language=source_language,
            target_language=target_language,
            duration=None,
        ),
    )


# =============================================================================
# History
# =============================================================================

@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=template_context(
            request,
            page="history",
            history=[],
        ),
    )


# =============================================================================
# Login
# =============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=template_context(
            request,
            page="login",
            next_path=request.query_params.get("next", "/dashboard"),
        ),
    )


# =============================================================================
# Login Submit
# =============================================================================

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    user = _get_auth_repository(request).authenticate(username, password)
    next_path = str(form.get("next", "/dashboard"))
    if not next_path.startswith("/") or next_path.startswith("//"):
        next_path = "/dashboard"

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=template_context(
                request,
                page="login",
                error="Invalid username or password.",
                next_path=next_path,
            ),
            status_code=401,
        )

    token = _get_auth_repository(request).create_session(user.id)
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=15 * 60,
        httponly=True,
        samesite="strict",
        secure=False,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _get_auth_repository(request).delete_session(token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/api/v1/session/keep-alive", status_code=204)
async def keep_session_alive():
    return Response(status_code=204)


# =============================================================================
# translations (Demo)
# =============================================================================
@router.get("/translations", response_class=HTMLResponse)
async def translations_page(request: Request):
    """
    Translation History page.
    """
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=template_context(
            request,
            page="history",
            history=[],
            page_title="Translation History",
        ),
    )


@router.get("/subtitles", response_class=HTMLResponse)
async def subtitles_page(request: Request):
    """
    Subtitle management page.
    """
    return templates.TemplateResponse(
        request=request,
        name="subtitles.html",
        context=template_context(
            request,
            page="subtitles",
            page_title="Subtitles",
        ),
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """
    Settings page.
    """
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=template_context(
            request,
            page="settings",
            page_title="Settings",
        ),
    )

@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """
    User management page.
    """
    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context=template_context(
            request,
            page="users",
            page_title="Users",
            users=_get_auth_repository(request).list_users(),
            roles=ROLES,
        ),
    )


@router.post("/users")
async def create_user(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    role = str(form.get("role", "user"))
    error = None
    try:
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        _get_auth_repository(request).create_user(username, password, role)
    except (ValueError, sqlite3.IntegrityError) as exc:
        error = "Username already exists." if isinstance(exc, sqlite3.IntegrityError) else str(exc)
    if error:
        return templates.TemplateResponse(
            request=request,
            name="users.html",
            context=template_context(
                request,
                page="users",
                page_title="Users",
                users=_get_auth_repository(request).list_users(),
                roles=ROLES,
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse("/users", status_code=303)


@router.post("/users/{user_id}/role")
async def update_user_role(user_id: int, request: Request):
    form = await request.form()
    try:
        _get_auth_repository(request).update_role(user_id, str(form.get("role", "")))
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="users.html",
            context=template_context(
                request,
                page="users",
                page_title="Users",
                users=_get_auth_repository(request).list_users(),
                roles=ROLES,
                error=str(exc),
            ),
            status_code=400,
        )
    return RedirectResponse("/users", status_code=303)


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context=template_context(
            request,
            page="logs",
        ),
    )


@router.get("/languages", response_class=HTMLResponse)
async def languages(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="languages.html",
        context=template_context(
            request,
            page="languages",
        ),
    )

@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="help.html",
        context=template_context(
            request,
            page="help",
        ),
    )    


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context=template_context(
            request,
            page="about",
        ),
    )    
