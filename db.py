"""SQLite persistence layer: user administration + job history.

Uses the stdlib sqlite3 module (no extra dependency). A short-lived
connection is opened per call - simple and safe for this app's scale
(a handful of concurrent local users), with WAL mode enabled so the
background pipeline thread and the web requests don't block each other.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from hmac import compare_digest

from app.config import DB_PATH, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME

logger = logging.getLogger(__name__)

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_USER = "user"
ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_USER)

_PBKDF2_ITERATIONS = 200_000
_init_lock = threading.Lock()
_initialized = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, _iterations, salt, _ = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = hash_password(password, salt=salt)
        return compare_digest(expected, stored_hash)
    except (ValueError, AttributeError):
        return False


def init_db() -> None:
    """Create tables if needed and seed the default admin user once."""
    global _initialized
    with _init_lock:
        if _initialized:
            return
        with get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','operator','user')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    detected_source_lang TEXT,
                    detected_source_lang_prob REAL,
                    stage TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    message TEXT,
                    error TEXT,
                    output_path TEXT,
                    logs TEXT,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
                """
            )
            existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            if existing == 0:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, is_active, created_at, updated_at) "
                    "VALUES (?, ?, ?, 1, ?, ?)",
                    (DEFAULT_ADMIN_USERNAME, hash_password(DEFAULT_ADMIN_PASSWORD), ROLE_ADMIN, _now(), _now()),
                )
                logger.info("Seeded default admin user '%s'", DEFAULT_ADMIN_USERNAME)
        _initialized = True


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

def get_user_by_username(username: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users ORDER BY username").fetchall()


def count_admins(exclude_id: int | None = None) -> int:
    with get_connection() as conn:
        if exclude_id is None:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = ? AND is_active = 1", (ROLE_ADMIN,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = ? AND is_active = 1 AND id != ?",
                (ROLE_ADMIN, exclude_id),
            ).fetchone()
        return row["c"]


def create_user(username: str, password: str, role: str) -> sqlite3.Row:
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?)",
            (username, hash_password(password), role, _now(), _now()),
        )
    return get_user_by_username(username)


def update_user(user_id: int, *, role: str | None = None, is_active: bool | None = None, password: str | None = None) -> None:
    fields, values = [], []
    if role is not None:
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role}")
        fields.append("role = ?")
        values.append(role)
    if is_active is not None:
        fields.append("is_active = ?")
        values.append(1 if is_active else 0)
    if password is not None:
        fields.append("password_hash = ?")
        values.append(hash_password(password))
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(_now())
    values.append(user_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def authenticate(username: str, password: str) -> sqlite3.Row | None:
    user = get_user_by_username(username)
    if user is None or not user["is_active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------

def create_job_row(job_id: str, username: str, filename: str, target_lang: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO jobs (id, username, filename, target_lang, stage, progress, message, done, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'queued', 0, 'Queued', 0, ?, ?)",
            (job_id, username, filename, target_lang, _now(), _now()),
        )


def update_job_row(job_id: str, **fields) -> None:
    if not fields:
        return
    column_map = {
        "stage": "stage",
        "progress": "progress",
        "message": "message",
        "detected_source_lang": "detected_source_lang",
        "detected_source_lang_prob": "detected_source_lang_prob",
        "error": "error",
        "output_path": "output_path",
        "logs": "logs",
        "done": "done",
    }
    sets, values = [], []
    for key, value in fields.items():
        column = column_map.get(key)
        if column is None:
            continue
        sets.append(f"{column} = ?")
        values.append(int(value) if column == "done" else value)
    if not sets:
        return
    sets.append("updated_at = ?")
    values.append(_now())
    values.append(job_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", values)


def get_job_row(job_id: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def list_job_rows(limit: int = 50, offset: int = 0, status: str | None = None, username: str | None = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM jobs"
    clauses, values = [], []
    if status:
        if status == "running":
            clauses.append("done = 0")
        elif status == "completed":
            clauses.append("stage = 'completed'")
        elif status == "failed":
            clauses.append("stage = 'failed'")
    if username:
        clauses.append("username = ?")
        values.append(username)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    values.extend([limit, offset])
    with get_connection() as conn:
        return conn.execute(query, values).fetchall()


def count_job_rows(status: str | None = None, username: str | None = None) -> int:
    query = "SELECT COUNT(*) AS c FROM jobs"
    clauses, values = [], []
    if status:
        if status == "running":
            clauses.append("done = 0")
        elif status == "completed":
            clauses.append("stage = 'completed'")
        elif status == "failed":
            clauses.append("stage = 'failed'")
    if username:
        clauses.append("username = ?")
        values.append(username)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    with get_connection() as conn:
        return conn.execute(query, values).fetchone()["c"]


def job_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
        running = conn.execute("SELECT COUNT(*) AS c FROM jobs WHERE done = 0").fetchone()["c"]
        completed = conn.execute("SELECT COUNT(*) AS c FROM jobs WHERE stage = 'completed'").fetchone()["c"]
        failed = conn.execute("SELECT COUNT(*) AS c FROM jobs WHERE stage = 'failed'").fetchone()["c"]
    return {"total": total, "running": running, "completed": completed, "failed": failed}


def delete_job_row(job_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def new_job_id() -> str:
    return uuid.uuid4().hex
