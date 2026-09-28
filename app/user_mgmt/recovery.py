from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.user_mgmt import models, repository, service
from app.user_mgmt.recovery_questions import question_text

SESSION_USER_ID = "recovery_user_id"
SESSION_TOKEN = "recovery_token"
SESSION_EXPIRES = "recovery_expires"
SESSION_ATTEMPTS = "recovery_attempts"


def begin(username: str, session: dict) -> tuple[str, list[str]] | None:
    user = repository.get_user_by_username(username.strip())
    if user is None or not user["is_active"] or not user["recovery_configured"]:
        return None
    questions = [question_text(user[f"recovery_question_{index}"]) for index in range(1, 4)]
    session[SESSION_USER_ID] = user["id"]
    session[SESSION_ATTEMPTS] = 0
    session.pop(SESSION_TOKEN, None)
    session.pop(SESSION_EXPIRES, None)
    return user["username"], questions


def verify(answers: tuple[str, str, str], session: dict) -> bool:
    user_id = session.get(SESSION_USER_ID)
    if not user_id:
        return False
    state = repository.recovery_attempt_state(int(user_id))
    if state is None:
        return False
    now = datetime.now(timezone.utc)
    locked_until = state["recovery_locked_until"]
    if locked_until and locked_until > now.isoformat(timespec="seconds"):
        return False
    attempts = int(state["recovery_attempts"] or 0) + 1
    if not service.verify_recovery_answers(int(user_id), answers):
        lock_until = (now + timedelta(seconds=models.RECOVERY_TTL_SECONDS)).isoformat(timespec="seconds") if attempts >= models.RECOVERY_MAX_ATTEMPTS else None
        repository.record_recovery_failure(int(user_id), attempts, lock_until)
        return False
    repository.clear_recovery_attempts(int(user_id))
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=models.RECOVERY_TTL_SECONDS)
    repository.set_recovery_authorization(
        int(user_id), hashlib.sha256(token.encode("utf-8")).hexdigest(), expires_at.isoformat(timespec="seconds")
    )
    session[SESSION_TOKEN] = token
    session[SESSION_EXPIRES] = expires_at.timestamp()
    return True


def complete(new_password: str, confirmation: str, session: dict) -> int:
    user_id = session.get(SESSION_USER_ID)
    token = session.get(SESSION_TOKEN)
    expires = session.get(SESSION_EXPIRES, 0)
    if not user_id or not token or float(expires) <= datetime.now(timezone.utc).timestamp():
        raise ValueError("Recovery authorization has expired or is invalid.")
    service.validate_password(new_password, confirmation)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not repository.consume_recovery_authorization(int(user_id), token_hash):
        raise ValueError("Recovery authorization has expired or is invalid.")
    service.reset_password(int(user_id), new_password, confirmation)
    for key in (SESSION_USER_ID, SESSION_TOKEN, SESSION_EXPIRES, SESSION_ATTEMPTS):
        session.pop(key, None)
    return int(user_id)


def clear(session: dict) -> None:
    for key in (SESSION_USER_ID, SESSION_TOKEN, SESSION_EXPIRES, SESSION_ATTEMPTS):
        session.pop(key, None)
