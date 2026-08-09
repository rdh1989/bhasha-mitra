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

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from infrastructure.security import UserRepository

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

user_repository = UserRepository()

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
        "current_user": request.session.get("username"),
        "current_role": request.session.get("role"),
    }

    context.update(kwargs)

    return context


def render_dashboard(request: Request):
    """
    Common dashboard renderer.
    """

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=template_context(
            request,
            page="dashboard",
            dashboard={
                "total_videos": 25,
                "completed": 22,
                "processing": 2,
                "failed": 1,
            },
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

    return templates.TemplateResponse(
        request=request,
        name="translation.html",
        context=template_context(
            request,
            page="translation",
            job_id="BM-20260724-0001",
            source_language="English",
            target_language="Marathi",
            duration="04:36",
        ),
    )


# =============================================================================
# History
# =============================================================================

@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):

    history_data = [
        {
            "filename": "Training.mp4",
            "size": "120 MB",
            "source_language": "English",
            "target_language": "Marathi",
            "duration": "04:36",
            "status": "Completed",
            "created_at": "24 Jul 2026",
        },
        {
            "filename": "Demo.mp4",
            "size": "86 MB",
            "source_language": "English",
            "target_language": "Hindi",
            "duration": "03:12",
            "status": "Running",
            "created_at": "23 Jul 2026",
        },
        {
            "filename": "Lecture.mp4",
            "size": "540 MB",
            "source_language": "English",
            "target_language": "Tamil",
            "duration": "21:40",
            "status": "Failed",
            "created_at": "20 Jul 2026",
        },
    ]

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=template_context(
            request,
            page="history",
            history=history_data,
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
        ),
    )


# =============================================================================
# Login Submit (Demo)
# =============================================================================

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    remember_me = form.get("remember_me") is not None

    user = user_repository.authenticate(username, password)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=template_context(
                request,
                page="login",
                error="Invalid username or password.",
                username=username,
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    request.session.clear()
    request.session.update(
        {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "remember_me": remember_me,
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(days=30 if remember_me else 1 / 3)
            ).timestamp(),
        }
    )

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# =============================================================================
# translations (Demo)
# =============================================================================
@router.get("/translations", response_class=HTMLResponse)
async def translations_page(request: Request):
    """
    Translation History page.
    """
    return templates.TemplateResponse(
    request,
    "history.html",
    {
        "page_title": "Translation History",
        "active_page": "history",
    },
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
        ),
    )


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
