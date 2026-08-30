"""FastAPI app: login, video upload, job orchestration, realtime status,
job history and user administration (SQLite-backed)."""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocketState

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
    require_api_auth,
    require_api_role,
    require_login_page,
    require_role_page,
)
from app.config import (
    ALLOWED_VIDEO_EXTENSIONS,
    ASR_COMPUTE_TYPE,
    ASR_CPU_THREADS,
    ASR_MODEL_DIR,
    ASR_NUM_WORKERS,
    LANGUAGES,
    MAX_CONCURRENT_JOBS,
    MAX_UPLOAD_BYTES,
    SESSION_SECRET,
    TORCH_NUM_THREADS,
    TRANSLATION_MODEL_DIR,
    TTS_MODEL_DIR,
    UPLOADS_DIR,
)
from app.jobs import JobManager
from app.logging_config import setup_logging
from app.models.asr import ASREngine
from app.models.translate import TranslationEngine
from app.models.tts import TTSEngine
from app.pipeline import run_pipeline

setup_logging()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Bhasha Mitra - AI Video Dubbing")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

db.init_db()

try:
    import torch

    torch.set_num_threads(TORCH_NUM_THREADS)
except Exception:
    logger.exception("Failed to set torch thread count")

job_manager = JobManager(max_workers=MAX_CONCURRENT_JOBS)
asr_engine = ASREngine(
    ASR_MODEL_DIR, compute_type=ASR_COMPUTE_TYPE, cpu_threads=ASR_CPU_THREADS, num_workers=ASR_NUM_WORKERS
)
translation_engine = TranslationEngine(TRANSLATION_MODEL_DIR)
tts_engine = TTSEngine(TTS_MODEL_DIR)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort safety net so an unexpected bug never crashes the server
    or leaks a raw traceback to the client; HTTPException still passes through."""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.on_event("startup")
def load_models_on_startup() -> None:
    """Load every model into memory once, up front, so the first submitted
    job doesn't pay the (multi-minute) load cost - every job just reuses
    these already-loaded engines."""
    logger.info("Bhasha Mitra starting up (asr_model_dir=%s)", ASR_MODEL_DIR)
    logger.info(
        "Concurrency: up to %d job(s) in parallel (asr_num_workers=%d, asr_cpu_threads=%d, torch_num_threads=%d)",
        MAX_CONCURRENT_JOBS, ASR_NUM_WORKERS, ASR_CPU_THREADS, TORCH_NUM_THREADS,
    )
    logger.info("Pre-loading ASR, translation and TTS models into memory - this can take a while...")
    started = time.monotonic()
    for name, engine in (("ASR", asr_engine), ("translation", translation_engine), ("TTS", tts_engine)):
        try:
            step_started = time.monotonic()
            engine.ensure_loaded()
            logger.info("%s model ready in %.1fs", name, time.monotonic() - step_started)
        except Exception:
            # Don't prevent the server from starting (login/history/etc. still
            # work) - the pipeline will retry loading and surface a clear
            # per-job error if this model is still broken when a job runs.
            logger.exception("Failed to pre-load the %s model at startup", name)
    logger.info("Model pre-loading finished in %.1fs", time.monotonic() - started)


@app.on_event("shutdown")
def unload_models_on_shutdown() -> None:
    """Mirror image of load_models_on_startup: release every model and free
    as much memory as possible before the process exits."""
    logger.info("Bhasha Mitra shutting down - unloading models and freeing memory...")
    job_manager.shutdown()
    for name, engine in (("ASR", asr_engine), ("translation", translation_engine), ("TTS", tts_engine)):
        try:
            engine.unload()
        except Exception:
            logger.exception("Failed to unload the %s model", name)

    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        logger.exception("Error while releasing torch memory during shutdown")
    logger.info("Shutdown cleanup complete.")


def _nav_context(request: Request) -> dict:
    """Common template context (current user + nav visibility) for every page."""
    user = current_user(request)
    return {"current_user": user, "can_trigger_jobs": user and user["role"] in JOB_TRIGGER_ROLES, "is_admin": user and user["role"] == ROLE_ADMIN}


def _language_labels() -> dict:
    return {lang.code: lang.label for lang in LANGUAGES}


def _public_user(row) -> dict:
    """Never expose password_hash (even hashed) to API clients."""
    data = dict(row)
    data.pop("password_hash", None)
    return data


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
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
        request, "login.html", {"error": "Invalid username or password"}, status_code=401
    )


@app.get("/logout")
def logout(request: Request):
    logger.info("User '%s' logged out", request.session.get(SESSION_USER_KEY))
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    stats = db.job_stats()
    recent_jobs = [dict(row) for row in db.list_job_rows(limit=8)]
    return templates.TemplateResponse(
        request, "dashboard.html",
        {**_nav_context(request), "languages": LANGUAGES, "languages_by_code": _language_labels(),
         "stats": stats, "recent_jobs": recent_jobs,
         "forbidden": request.query_params.get("error") == "forbidden"},
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request, "history.html",
        {**_nav_context(request), "languages": LANGUAGES, "languages_by_code": _language_labels()},
    )


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    redirect = require_role_page(request, ROLE_ADMIN)
    if redirect:
        return redirect
    users = [_public_user(row) for row in db.list_users()]
    return templates.TemplateResponse(request, "users.html", {**_nav_context(request), "users": users, "roles": ROLES})


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(request, "about.html", {**_nav_context(request), "languages": LANGUAGES})


@app.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    redirect = require_login_page(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(request, "help.html", _nav_context(request))


# --------------------------------------------------------------------------
# Jobs API
# --------------------------------------------------------------------------

def _save_upload(job_id: str, video: UploadFile, suffix: str) -> tuple[Path, int]:
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    video_path = job_dir / f"input{suffix}"
    size = 0
    with open(video_path, "wb") as out_file:
        while chunk := video.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail=f"'{video.filename}' is too large.")
            out_file.write(chunk)
    return video_path, size


@app.post("/api/jobs")
async def create_jobs(
    request: Request,
    video: list[UploadFile] = File(...),
    target_lang: str = Form(...),
):
    """Accepts one or more video files in a single submission - each becomes
    its own job so multiple translation jobs can be queued at once."""
    user = require_api_role(request, *JOB_TRIGGER_ROLES)

    valid_codes = {lang.code for lang in LANGUAGES}
    if target_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown target language.")
    if not video:
        raise HTTPException(status_code=400, detail="No video files provided.")

    job_ids: list[str] = []
    for video_file in video:
        suffix = Path(video_file.filename or "").suffix.lower()
        if suffix not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}' for '{video_file.filename}'.")

        job = job_manager.create(target_lang=target_lang, filename=video_file.filename or "video", username=user["username"])
        try:
            video_path, size = _save_upload(job.id, video_file, suffix)
        except HTTPException:
            shutil.rmtree(UPLOADS_DIR / job.id, ignore_errors=True)
            raise
        except Exception:
            logger.exception("Failed to save uploaded file for job %s", job.id)
            shutil.rmtree(UPLOADS_DIR / job.id, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"Failed to save '{video_file.filename}'.")
        finally:
            video_file.file.close()

        logger.info(
            "Job %s created by '%s': file='%s' size=%d bytes target_lang=%s",
            job.id, user["username"], video_file.filename, size, target_lang,
        )
        job_manager.update(job.id, message="Upload received. Queued for processing.")
        job_manager.submit(
            run_pipeline, job.id, str(video_path), target_lang, job_manager, asr_engine, translation_engine, tts_engine
        )
        job_ids.append(job.id)

    return {"job_ids": job_ids}


@app.get("/api/jobs")
def list_jobs(request: Request, limit: int = 20, offset: int = 0, status: str | None = None):
    require_api_auth(request)
    limit = max(1, min(limit, 200))
    rows = [dict(row) for row in db.list_job_rows(limit=limit, offset=offset, status=status)]
    total = db.count_job_rows(status=status)
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/jobs/{job_id}")
def get_job(request: Request, job_id: str):
    require_api_auth(request)
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job.to_public_dict())


@app.delete("/api/jobs/{job_id}")
def delete_job(request: Request, job_id: str):
    require_api_role(request, ROLE_ADMIN)
    row = db.get_job_row(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    shutil.rmtree(UPLOADS_DIR / job_id, ignore_errors=True)
    if row["output_path"]:
        Path(row["output_path"]).unlink(missing_ok=True)
    db.delete_job_row(job_id)
    logger.info("Job %s deleted by admin '%s'", job_id, request.session.get(SESSION_USER_KEY))
    return {"ok": True}


@app.get("/api/stats")
def get_stats(request: Request):
    require_api_auth(request)
    return db.job_stats()


@app.get("/media/output/{job_id}")
def get_output(request: Request, job_id: str):
    require_api_auth(request)
    job = job_manager.get(job_id)
    if job is None or not job.output_path or not Path(job.output_path).exists():
        logger.warning("Output requested but not available for job %s", job_id)
        raise HTTPException(status_code=404, detail="Output not available")
    logger.info("Serving output video for job %s", job_id)
    return FileResponse(job.output_path, media_type="video/mp4", filename=f"dubbed_{job.filename}.mp4")


@app.websocket("/ws/{job_id}")
async def job_status_ws(websocket: WebSocket, job_id: str):
    if not is_logged_in(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    logger.info("WebSocket connected for job %s", job_id)
    try:
        last_payload = None
        while True:
            job = job_manager.get(job_id)
            if job is None:
                logger.warning("WebSocket requested unknown job %s", job_id)
                await websocket.send_json({"error": "Job not found"})
                break
            payload = job.to_public_dict()
            if payload != last_payload:
                await websocket.send_json(payload)
                last_payload = payload
            if job.done:
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for job %s", job_id)
    except Exception:
        logger.exception("WebSocket error for job %s", job_id)
    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()


# --------------------------------------------------------------------------
# User administration API (admin only)
# --------------------------------------------------------------------------

def _ensure_not_last_admin(user_row, demoting: bool = False, deactivating: bool = False, deleting: bool = False) -> None:
    if user_row["role"] != ROLE_ADMIN:
        return
    if not (demoting or deactivating or deleting):
        return
    if db.count_admins(exclude_id=user_row["id"]) == 0:
        raise HTTPException(status_code=400, detail="Cannot remove the last remaining admin account.")


@app.get("/api/users")
def api_list_users(request: Request):
    require_api_role(request, ROLE_ADMIN)
    return {"items": [_public_user(row) for row in db.list_users()]}


@app.post("/api/users")
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


@app.put("/api/users/{user_id}")
def api_update_user(
    request: Request,
    user_id: int,
    role: str | None = Form(None),
    is_active: bool | None = Form(None),
    password: str | None = Form(None),
):
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


@app.delete("/api/users/{user_id}")
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

