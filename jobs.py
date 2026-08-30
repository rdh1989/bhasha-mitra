"""In-memory job tracking + a bounded worker pool so several CPU-bound
pipeline runs can happen at once (extra uploads beyond the pool size queue
automatically).

Every create/update is also written through to the SQLite `jobs` table
(see app/db.py) so job history survives server restarts and can be listed
independently of what is currently in memory.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app import db

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    id: str
    target_lang: str
    filename: str
    username: str = ""
    stage: str = "queued"
    progress: float = 0.0
    message: str = "Queued"
    detected_source_lang: str | None = None
    detected_source_lang_prob: float | None = None
    error: str | None = None
    output_path: str | None = None
    logs: list[str] = field(default_factory=list)
    done: bool = False
    created_at: float = field(default_factory=time.time)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "target_lang": self.target_lang,
            "filename": self.filename,
            "username": self.username,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "message": self.message,
            "detected_source_lang": self.detected_source_lang,
            "detected_source_lang_prob": self.detected_source_lang_prob,
            "error": self.error,
            "has_output": self.output_path is not None,
            "logs": self.logs[-200:],
            "done": self.done,
        }

    @classmethod
    def from_db_row(cls, row) -> "JobState":
        logs = row["logs"].split("\n") if row["logs"] else []
        return cls(
            id=row["id"],
            target_lang=row["target_lang"],
            filename=row["filename"],
            username=row["username"],
            stage=row["stage"],
            progress=row["progress"] or 0.0,
            message=row["message"] or "",
            detected_source_lang=row["detected_source_lang"],
            detected_source_lang_prob=row["detected_source_lang_prob"],
            error=row["error"],
            output_path=row["output_path"],
            logs=logs,
            done=bool(row["done"]),
        )


class JobManager:
    def __init__(self, max_workers: int = 1):
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def create(self, target_lang: str, filename: str, username: str = "") -> JobState:
        job_id = db.new_job_id()
        state = JobState(id=job_id, target_lang=target_lang, filename=filename, username=username)
        with self._lock:
            self._jobs[job_id] = state
        try:
            db.create_job_row(job_id, username, filename, target_lang)
        except Exception:
            logger.exception("Failed to persist new job %s to the database", job_id)
        logger.info("Job %s created (user=%s, target_lang=%s, filename=%s)", job_id, username, target_lang, filename)
        return state

    def get(self, job_id: str) -> JobState | None:
        with self._lock:
            state = self._jobs.get(job_id)
        if state is not None:
            return state
        # Not in memory (e.g. server restarted since the job ran) - fall back to DB.
        row = db.get_job_row(job_id)
        return JobState.from_db_row(row) if row else None

    def update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                logger.warning("Attempted to update unknown job %s", job_id)
                return
            for key, value in kwargs.items():
                setattr(job, key, value)
            if "message" in kwargs and kwargs["message"]:
                job.logs.append(kwargs["message"])
            logs_snapshot = "\n".join(job.logs[-500:])
        if "error" in kwargs and kwargs["error"]:
            logger.error("Job %s failed: %s", job_id, kwargs["error"])
        elif "message" in kwargs and kwargs["message"]:
            logger.info("Job %s: %s", job_id, kwargs["message"])
        try:
            db.update_job_row(job_id, **kwargs, logs=logs_snapshot)
        except Exception:
            logger.exception("Failed to persist update for job %s to the database", job_id)

    def submit(self, fn, *args, **kwargs) -> None:
        self._executor.submit(self._run_safely, fn, *args, **kwargs)

    def shutdown(self) -> None:
        """Stop accepting new work. Any job already running keeps running to
        completion in its thread (Python cannot force-stop it mid-way), but
        anything still queued is cancelled so the process can exit promptly."""
        try:
            pending = self._executor._work_queue.qsize()
            if pending:
                logger.warning("Shutting down job executor with %d job(s) still queued; they will not run.", pending)
        except AttributeError:
            pass
        self._executor.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._jobs.clear()
        logger.info("Job manager shut down")

    @staticmethod
    def _run_safely(fn, *args, **kwargs) -> None:
        """Safety net: fn (run_pipeline) already handles its own errors, but
        this guarantees a bug there can never silently kill a worker thread
        or vanish an exception inside the executor."""
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("Unhandled exception while running background job")

