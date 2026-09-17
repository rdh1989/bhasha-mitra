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
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app import db
from app.models.memory_policy import get_memory_policy

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    """Raised by the pipeline at a safe cancellation checkpoint."""


@dataclass
class JobState:
    id: str
    source_lang: str
    target_lang: str
    filename: str
    source_path: str = ""
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
    cancel_requested: bool = False
    created_at: float = field(default_factory=time.time)
    ended_at: str | None = None
    duration_seconds: float | None = None

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "source_lang": self.source_lang,
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
            "cancel_requested": self.cancel_requested,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_db_row(cls, row) -> "JobState":
        logs = row["logs"].split("\n") if row["logs"] else []
        return cls(
            id=row["id"],
            source_lang=row["source_lang"] or "",
            target_lang=row["target_lang"],
            filename=row["filename"],
            source_path=row["source_path"] or "",
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
            cancel_requested=bool(row["cancel_requested"]),
            ended_at=row["ended_at"],
            duration_seconds=row["duration_seconds"],
        )


class JobManager:
    def __init__(self, max_workers: int = 1, max_translation_jobs: int = 1, memory_policy=None):
        if max_translation_jobs < 1:
            raise ValueError("max_translation_jobs must be at least 1")
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._queue = deque()
        self._active_jobs = 0
        self._active_text_jobs = 0
        self._max_translation_jobs = max_translation_jobs
        self._memory_policy = memory_policy or get_memory_policy()
        self._shutdown_requested = False
        self._dispatcher = threading.Thread(target=self._dispatch, daemon=True)
        self._dispatcher.start()

    def create(self, source_lang: str, target_lang: str, filename: str, source_path: str, username: str = "") -> JobState:
        job_id = db.new_job_id()
        state = JobState(
            id=job_id, source_lang=source_lang, target_lang=target_lang, filename=filename, source_path=source_path, username=username,
        )
        with self._lock:
            self._jobs[job_id] = state
        try:
            db.create_job_row(job_id, username, filename, source_lang, target_lang, source_path)
        except Exception:
            logger.exception("Failed to persist new job %s to the database", job_id)
        logger.info("Job %s created (user=%s, source_lang=%s, target_lang=%s, filename=%s)", job_id, username, source_lang, target_lang, filename)
        return state

    def retry(self, job_id: str) -> JobState | None:
        """Requeue a failed persisted job under its original ID.

        Its output directory is intentionally retained: run_pipeline checks
        completed artifacts there and resumes at the first missing stage.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                row = db.get_job_row(job_id)
                if row is None:
                    return None
                job = JobState.from_db_row(row)
                self._jobs[job_id] = job
            if job.stage not in ("failed", "cancelled"):
                return None
            job.stage = "queued"
            job.progress = 0.0
            job.message = "Retry queued; resuming from saved work."
            job.error = None
            job.output_path = None
            job.done = False
            job.cancel_requested = False
            job.ended_at = None
            job.duration_seconds = None
            job.created_at = time.time()
            job.logs.append(job.message)
            logs_snapshot = "\n".join(job.logs[-500:])
        db.update_job_row(
            job_id,
            stage="queued",
            progress=0.0,
            message=job.message,
            error=None,
            output_path=None,
            done=False,
            cancel_requested=False,
            ended_at=None,
            duration_seconds=None,
            logs=logs_snapshot,
        )
        logger.info("Job %s: %s", job_id, job.message)
        return job

    def request_cancel(self, job_id: str) -> JobState | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.cancel_requested or job.stage == "cancelled":
                return job
            if job.done:
                return None
            job.cancel_requested = True
            if job.stage == "queued":
                job.stage = "cancelled"
                job.done = True
                job.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                job.duration_seconds = round(time.time() - job.created_at, 1)
                job.message = "Cancelled."
                self._queue = deque(
                    queued for queued in self._queue
                    if not queued[2] or queued[2][0] != job_id
                )
                self._condition.notify_all()
            else:
                job.stage = "cancelling"
                job.message = "Cancellation requested; stopping at the next safe checkpoint."
            job.logs.append(job.message)
            logs_snapshot = "\n".join(job.logs[-500:])
        db.update_job_row(
            job_id,
            stage=job.stage,
            message=job.message,
            cancel_requested=True,
            done=job.done,
            ended_at=job.ended_at,
            duration_seconds=job.duration_seconds,
            logs=logs_snapshot,
        )
        logger.info("Job %s: %s", job_id, job.message)
        return job

    def raise_if_cancelled(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None and job.cancel_requested:
                raise JobCancelled()

    def mark_cancelled(self, job_id: str) -> None:
        self.update(job_id, stage="cancelled", done=True, message="Cancelled.")

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
            if job.done and job.cancel_requested:
                return
            if job.cancel_requested and kwargs.get("stage") == "completed":
                kwargs = {"stage": "cancelled", "done": True, "message": "Cancelled.", "output_path": None}
            if kwargs.get("done") and not job.done:
                # First time this job finishes (completed or failed) - record
                # when it ended and how long the whole run took.
                kwargs.setdefault("ended_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
                kwargs.setdefault("duration_seconds", round(time.time() - job.created_at, 1))
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
        with self._condition:
            self._queue.append((False, fn, args, kwargs))
            self._condition.notify_all()

    def submit_text(self, fn, *args, **kwargs) -> None:
        """Queue text work in its single reserved admission slot."""
        with self._condition:
            self._queue.append((True, fn, args, kwargs))
            self._condition.notify_all()

    @property
    def active_job_count(self) -> int:
        with self._lock:
            return self._active_jobs

    @property
    def queued_job_count(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def active_text_job_count(self) -> int:
        with self._lock:
            return self._active_text_jobs

    def shutdown(self) -> None:
        """Cancel all work without waiting for long native model calls.

        Job threads are daemon threads, so Ctrl+C can stop the process even
        if a worker is currently inside ASR or translation native code that
        Python cannot interrupt safely.
        """
        with self._condition:
            self._shutdown_requested = True
            active_ids = [job_id for job_id, job in self._jobs.items() if not job.done]
            self._queue.clear()
            self._condition.notify_all()
        for job_id in active_ids:
            self.request_cancel(job_id)
        with self._lock:
            pending_cancelled = [job_id for job_id, job in self._jobs.items() if job.cancel_requested and not job.done]
        for job_id in pending_cancelled:
            self.mark_cancelled(job_id)
        logger.info("Job manager shut down")

    def _dispatch(self) -> None:
        while True:
            with self._condition:
                while not self._shutdown_requested and not self._next_admissible_job():
                    self._condition.wait()
                if self._shutdown_requested:
                    return
                if not self._memory_policy.can_start_translation_job():
                    self._condition.wait(timeout=1.0)
                    continue
                is_text, fn, args, kwargs = self._next_admissible_job()
                self._queue.remove((is_text, fn, args, kwargs))
                if is_text:
                    self._active_text_jobs += 1
                else:
                    self._active_jobs += 1
            thread = threading.Thread(target=self._run_admitted, args=(is_text, fn, args, kwargs), daemon=True)
            thread.start()

    def _next_admissible_job(self):
        for job in self._queue:
            is_text, *_rest = job
            if is_text and self._active_text_jobs < 1:
                return job
            if not is_text and self._active_jobs < self._max_translation_jobs:
                return job
        return None

    def _run_admitted(self, is_text, fn, args, kwargs) -> None:
        try:
            self._run_safely(fn, *args, **kwargs)
        finally:
            with self._condition:
                if is_text:
                    self._active_text_jobs -= 1
                else:
                    self._active_jobs -= 1
                self._condition.notify_all()

    @staticmethod
    def _run_safely(fn, *args, **kwargs) -> None:
        """Safety net: fn (run_pipeline) already handles its own errors, but
        this guarantees a bug there can never silently kill a worker thread
        or vanish an exception inside the executor."""
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("Unhandled exception while running background job")

