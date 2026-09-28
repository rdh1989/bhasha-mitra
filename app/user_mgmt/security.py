from __future__ import annotations

from app.db import hash_password, verify_password


def normalize_recovery_answer(answer: str) -> str:
    return " ".join(answer.strip().casefold().split())


def hash_recovery_answer(answer: str) -> str:
    normalized = normalize_recovery_answer(answer)
    return hash_password(normalized)


def verify_recovery_answer(answer: str, stored_hash: str) -> bool:
    normalized = normalize_recovery_answer(answer)
    return bool(normalized) and verify_password(normalized, stored_hash)
