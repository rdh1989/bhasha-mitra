"""FastAPI app: login, local video path job orchestration, realtime status,
job history and user administration (SQLite-backed)."""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
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
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_TEXT_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    ASR_COMPUTE_TYPE,
    ASR_CPU_THREADS,
    ASR_MODEL_DIR,
    ASR_NUM_WORKERS,
    ASR_PROVIDER_BY_LANGUAGE,
    INDIC_ASR_DECODING,
    INDIC_ASR_ENABLED,
    INDIC_ASR_MODEL_DIR,
    LANGUAGES,
    MAX_CONCURRENT_JOBS,
    MAX_PARALLEL_TRANSLATION_JOBS,
    OUTPUTS_DIR,
    PIPER_VOICES_DIR,
    SESSION_SECRET,
    TORCH_NUM_THREADS,
    TRANSLATION_INDIC_EN_MODEL_DIR,
    TRANSLATION_INDIC_INDIC_MODEL_DIR,
    TRANSLATION_MODEL_DIR,
    TRANSLATION_MODEL_SIZE,
    TTS_ENGINE,
    TTS_MODEL_DIR,
)
from app.fs_browse import list_directory
from app.jobs import JobManager
from app.logging_config import setup_logging
from app.models.asr import ASREngine
from app.models.indic_asr import IndicASREngine
from app.models.piper_tts import PiperTTSEngine
from app.models.translate import TranslationEngine
from app.models.tts import TTSEngine
from app.pipeline import run_audio_pipeline, run_pipeline, run_text_pipeline, translate_text

setup_logging()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Bhasha Mitra - AI Video Dubbing")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

db.init_db()
db.fail_interrupted_jobs()

try:
    import torch

    torch.set_num_threads(TORCH_NUM_THREADS)
except Exception:
    logger.exception("Failed to set torch thread count")

job_manager = JobManager(
    max_workers=MAX_CONCURRENT_JOBS,
    max_translation_jobs=MAX_PARALLEL_TRANSLATION_JOBS,
)
indic_asr_engine = IndicASREngine(INDIC_ASR_MODEL_DIR, decoding=INDIC_ASR_DECODING)
asr_engine = ASREngine(
    ASR_MODEL_DIR, compute_type=ASR_COMPUTE_TYPE, cpu_threads=ASR_CPU_THREADS, num_workers=ASR_NUM_WORKERS,
    indic_asr=indic_asr_engine,
)
translation_engine = TranslationEngine(TRANSLATION_MODEL_DIR)
translation_indic_engine = TranslationEngine(TRANSLATION_INDIC_INDIC_MODEL_DIR)
translation_indic_en_engine = TranslationEngine(TRANSLATION_INDIC_EN_MODEL_DIR)
tts_engine = PiperTTSEngine(PIPER_VOICES_DIR) if TTS_ENGINE == "piper" else TTSEngine(TTS_MODEL_DIR)
logger.info("TTS engine: %s", TTS_ENGINE)
logger.info("Translation model size: %s", TRANSLATION_MODEL_SIZE)
logger.info("Indic ASR decoding: %s", INDIC_ASR_DECODING)


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
    for name, engine in (
        ("ASR", asr_engine),
        ("translation (en-indic)", translation_engine),
        ("translation (indic-indic)", translation_indic_engine),
        ("translation (indic-en)", translation_indic_en_engine),
        ("Indic ASR refinement", indic_asr_engine),
        ("TTS", tts_engine),
    ):
        if engine is None:
            continue
        try:
            step_started = time.monotonic()
            engine.ensure_loaded()
            logger.info("%s model ready in %.1fs", name, time.monotonic() - step_started)
        except Exception:
            # Check if this is a memory policy rejection
            import traceback
            tb = traceback.format_exc()
            if "Memory policy" in tb:
                logger.warning(
                    "Skipping %s model at startup due to memory policy constraint. "
                    "The model will be loaded on-demand if memory becomes available. "
                    "Current state: %s", name, tb.split('\n')[-2]
                )
            else:
                # Other failures - don't prevent server start (login/history/etc. still work)
                # The pipeline will retry loading and surface a clear per-job error
                logger.exception("Failed to pre-load the %s model at startup", name)
    logger.info("Model pre-loading finished in %.1fs", time.monotonic() - started)


@app.on_event("shutdown")
def unload_models_on_shutdown() -> None:
    """Mirror image of load_models_on_startup: release every model and free
    as much memory as possible before the process exits."""
    logger.info("Bhasha Mitra shutting down - unloading models and freeing memory...")
    job_manager.shutdown()
    for name, engine in (
        ("ASR", asr_engine),
        ("translation (en-indic)", translation_engine),
        ("translation (indic-indic)", translation_indic_engine),
        ("translation (indic-en)", translation_indic_en_engine),
        ("Indic ASR refinement", indic_asr_engine),
        ("TTS", tts_engine),
    ):
        if engine is None:
            continue
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

@app.get("/api/browse")
def browse_filesystem(request: Request, path: str = "", kind: str = "video"):
    """Backs the dashboard's video file picker - lets an operator/admin
    browse this machine's filesystem and pick a full path without ever
    uploading the file."""
    require_api_role(request, *JOB_TRIGGER_ROLES)
    if kind not in ("video", "audio", "text"):
        raise HTTPException(status_code=400, detail="Browse kind must be 'video', 'audio', or 'text'.")
    try:
        return list_directory(path or None, kind=kind)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class CreateJobsRequest(BaseModel):
    video_paths: list[str]
    source_lang: str
    target_lang: str


class CreateAudioJobsRequest(BaseModel):
    audio_paths: list[str]
    source_lang: str
    target_lang: str


class TranslateTextRequest(BaseModel):
    text: str = ""
    text_path: str | None = None
    source_lang: str
    target_lang: str


class CreateTextJobRequest(TranslateTextRequest):
    pass


@app.post("/api/jobs")
def create_jobs(request: Request, payload: CreateJobsRequest):
    """Accepts one or more local video file paths in a single submission -
    each becomes its own job so multiple translation jobs can be queued at
    once. The app runs locally, so videos are read directly from their
    existing path on disk instead of being uploaded/copied."""
    user = require_api_role(request, *JOB_TRIGGER_ROLES)

    valid_codes = {lang.code for lang in LANGUAGES}
    if payload.source_lang not in ASR_PROVIDER_BY_LANGUAGE:
        raise HTTPException(status_code=400, detail="No ASR is configured for the selected source language.")
    if payload.target_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown target language.")

    raw_paths = [p.strip().strip('"') for p in payload.video_paths if p.strip()]
    if not raw_paths:
        raise HTTPException(status_code=400, detail="No video paths provided.")

    job_ids: list[str] = []
    for raw_path in raw_paths:
        video_path = Path(raw_path)
        if not video_path.is_absolute():
            raise HTTPException(status_code=400, detail=f"'{raw_path}' must be an absolute path.")
        suffix = video_path.suffix.lower()
        if suffix not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}' for '{raw_path}'.")
        if not video_path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: '{raw_path}'.")
        video_path = video_path.resolve()

        job = job_manager.create(
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
            filename=video_path.name,
            source_path=str(video_path),
            username=user["username"],
        )
        logger.info(
            "Job %s created by '%s': path='%s' source_lang=%s target_lang=%s",
            job.id, user["username"], video_path, payload.source_lang, payload.target_lang,
        )
        job_manager.update(job.id, message="Queued for processing.")
        job_manager.submit(
            run_pipeline, job.id, str(video_path), payload.source_lang, payload.target_lang, job_manager, asr_engine,
            translation_engine, translation_indic_engine, translation_indic_en_engine, tts_engine,
        )
        job_ids.append(job.id)

    return {"job_ids": job_ids}


@app.post("/api/audio/jobs")
def create_audio_jobs(request: Request, payload: CreateAudioJobsRequest):
    user = require_api_role(request, *JOB_TRIGGER_ROLES)
    valid_codes = {lang.code for lang in LANGUAGES}
    if payload.source_lang not in ASR_PROVIDER_BY_LANGUAGE:
        raise HTTPException(status_code=400, detail="No ASR is configured for the selected source language.")
    if payload.target_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown target language.")
    raw_paths = [path.strip().strip('"') for path in payload.audio_paths if path.strip()]
    if not raw_paths:
        raise HTTPException(status_code=400, detail="No audio paths provided.")

    job_ids: list[str] = []
    for raw_path in raw_paths:
        audio_path = Path(raw_path)
        if not audio_path.is_absolute():
            raise HTTPException(status_code=400, detail=f"'{raw_path}' must be an absolute path.")
        suffix = audio_path.suffix.lower()
        if suffix not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}' for '{raw_path}'.")
        if not audio_path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: '{raw_path}'.")
        audio_path = audio_path.resolve()
        job = job_manager.create(
            source_lang=payload.source_lang, target_lang=payload.target_lang,
            filename=audio_path.name, source_path=str(audio_path), username=user["username"],
        )
        job_manager.update(job.id, message="Queued for processing.")
        job_manager.submit(
            run_audio_pipeline, job.id, str(audio_path), payload.source_lang, payload.target_lang,
            job_manager, asr_engine, translation_engine, translation_indic_engine,
            translation_indic_en_engine, tts_engine,
        )
        job_ids.append(job.id)
    return {"job_ids": job_ids}


@app.post("/api/text/translate")
def translate_text_request(request: Request, payload: TranslateTextRequest):
    require_api_role(request, *JOB_TRIGGER_ROLES)
    text = payload.text.strip()
    if payload.text_path:
        text_path = Path(payload.text_path.strip().strip('"'))
        if not text_path.is_absolute():
            raise HTTPException(status_code=400, detail="Text path must be absolute.")
        if text_path.suffix.lower() not in ALLOWED_TEXT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Only .txt files are supported.")
        if not text_path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: '{payload.text_path}'.")
        try:
            text = text_path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="TXT files must be UTF-8 encoded.") from exc
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")
    valid_codes = {lang.code for lang in LANGUAGES}
    if payload.source_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown source language.")
    if payload.target_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown target language.")
    try:
        translated_text = translate_text(
            text, payload.source_lang, payload.target_lang,
            translation_engine, translation_indic_engine, translation_indic_en_engine,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"translated_text": translated_text}


@app.post("/api/text/jobs")
def create_text_job(request: Request, payload: CreateTextJobRequest):
    user = require_api_role(request, *JOB_TRIGGER_ROLES)
    text = payload.text.strip()
    text_path = None
    if payload.text_path:
        text_path = Path(payload.text_path.strip().strip('"'))
        if not text_path.is_absolute():
            raise HTTPException(status_code=400, detail="Text path must be absolute.")
        if text_path.suffix.lower() not in ALLOWED_TEXT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Only .txt files are supported.")
        if not text_path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: '{payload.text_path}'.")
    if not text and text_path is None:
        raise HTTPException(status_code=400, detail="Text is required.")
    valid_codes = {lang.code for lang in LANGUAGES}
    if payload.source_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown source language.")
    if payload.target_lang not in valid_codes:
        raise HTTPException(status_code=400, detail="Unknown target language.")

    job = job_manager.create(
        source_lang=payload.source_lang,
        target_lang=payload.target_lang,
        filename=text_path.name if text_path else "typed-text.txt",
        source_path=str(text_path) if text_path else "",
        username=user["username"],
    )
    if text_path is None:
        input_path = OUTPUTS_DIR / "typed-text" / job.id / "input.txt"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(text, encoding="utf-8")
        job_manager.update(job.id, source_path=str(input_path))
        text_path = input_path
    job_manager.update(job.id, message="Queued for processing.")
    job_manager.submit_text(
        run_text_pipeline, job.id, str(text_path), payload.source_lang, payload.target_lang,
        job_manager, translation_engine, translation_indic_engine, translation_indic_en_engine,
    )
    return {"job_id": job.id}


@app.post("/api/jobs/{job_id}/retry")
def retry_job(request: Request, job_id: str):
    require_api_role(request, *JOB_TRIGGER_ROLES)
    row = db.get_job_row(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["stage"] not in ("failed", "cancelled"):
        raise HTTPException(status_code=409, detail="Only failed or cancelled jobs can be retried")
    source_path = Path(row["source_path"] or "")
    if not source_path.is_file():
        raise HTTPException(
            status_code=409,
            detail="The original source video path is unavailable; submit the video again.",
        )
    job = job_manager.retry(job_id)
    if job is None:
        raise HTTPException(status_code=409, detail="Job could not be requeued")
    if source_path.suffix.lower() in ALLOWED_TEXT_EXTENSIONS:
        job_manager.submit_text(
            run_text_pipeline, job.id, str(source_path), job.source_lang, job.target_lang,
            job_manager, translation_engine, translation_indic_engine, translation_indic_en_engine,
        )
    else:
        pipeline = run_audio_pipeline if source_path.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS else run_pipeline
        job_manager.submit(
            pipeline, job.id, str(source_path), job.source_lang, job.target_lang, job_manager, asr_engine,
            translation_engine, translation_indic_engine, translation_indic_en_engine, tts_engine,
        )
    return {"job_id": job.id, "message": job.message}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str):
    require_api_role(request, *JOB_TRIGGER_ROLES)
    job = job_manager.request_cancel(job_id)
    if job is None:
        row = db.get_job_row(job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=409, detail="Job is already finished or being cancelled")
    return {"job_id": job.id, "message": job.message}


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
    # Only remove our own generated outputs/<video>/<job_id>/ working
    # directory - the source video lives outside our storage and is never
    # touched (never uploaded/copied in the first place).
    video_stem = Path(row["filename"]).stem if row["filename"] else None
    if video_stem:
        shutil.rmtree(OUTPUTS_DIR / video_stem / job_id, ignore_errors=True)
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
    if Path(job.output_path).suffix.lower() == ".wav":
        return FileResponse(job.output_path, media_type="audio/wav", filename=f"dubbed_{Path(job.filename).stem}.wav")
    if Path(job.output_path).suffix.lower() == ".txt":
        return FileResponse(job.output_path, media_type="text/plain", filename=f"translated_{Path(job.filename).stem}.txt")
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

