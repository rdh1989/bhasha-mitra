from __future__ import annotations

from datetime import datetime, timezone

from app import db


def get_user(user_id: int):
    return db.get_user_by_id(user_id)


def get_user_by_username(username: str):
    return db.get_user_by_username(username)


def create_user(
    username: str,
    password_hash: str,
    questions: tuple[str, str, str],
    answer_hashes: tuple[str, str, str],
):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, is_active, "
            "recovery_question_1, recovery_answer_hash_1, recovery_question_2, recovery_answer_hash_2, "
            "recovery_question_3, recovery_answer_hash_3, recovery_configured, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (username, password_hash, db.ROLE_USER,
             questions[0], answer_hashes[0], questions[1], answer_hashes[1],
             questions[2], answer_hashes[2],
             _now(), _now()),
        )
    return get_user_by_username(username)


def update_recovery_configuration(user_id: int, questions: tuple[str, str, str], answer_hashes: tuple[str, str, str]) -> None:
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE users SET recovery_question_1 = ?, recovery_answer_hash_1 = ?, "
            "recovery_question_2 = ?, recovery_answer_hash_2 = ?, recovery_question_3 = ?, "
            "recovery_answer_hash_3 = ?, recovery_configured = 1, updated_at = ? WHERE id = ?",
            (questions[0], answer_hashes[0], questions[1], answer_hashes[1],
             questions[2], answer_hashes[2], _now(), user_id),
        )


def set_recovery_authorization(user_id: int, token_hash: str, expires_at: str) -> None:
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE users SET recovery_reset_token_hash = ?, recovery_reset_expires_at = ?, "
            "recovery_reset_used_at = NULL, updated_at = ? WHERE id = ?",
            (token_hash, expires_at, _now(), user_id),
        )


def recovery_attempt_state(user_id: int):
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT recovery_attempts, recovery_locked_until FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def record_recovery_failure(user_id: int, attempts: int, locked_until: str | None) -> None:
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE users SET recovery_attempts = ?, recovery_locked_until = ?, updated_at = ? WHERE id = ?",
            (attempts, locked_until, _now(), user_id),
        )


def clear_recovery_attempts(user_id: int) -> None:
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE users SET recovery_attempts = 0, recovery_locked_until = NULL, updated_at = ? WHERE id = ?",
            (_now(), user_id),
        )


def consume_recovery_authorization(user_id: int, token_hash: str) -> bool:
    now = _now()
    with db.get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET recovery_reset_used_at = ?, recovery_reset_token_hash = NULL, "
            "recovery_reset_expires_at = NULL, updated_at = ? "
            "WHERE id = ? AND recovery_reset_token_hash = ? "
            "AND recovery_reset_expires_at > ? AND recovery_reset_used_at IS NULL",
            (now, now, user_id, token_hash, now),
        )
    return cursor.rowcount == 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
