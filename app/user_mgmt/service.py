from __future__ import annotations

from app import db
from app.user_mgmt import repository
from app.user_mgmt.recovery_questions import QUESTION_IDS
from app.user_mgmt.security import hash_recovery_answer, verify_recovery_answer

MIN_PASSWORD_LENGTH = 8


def validate_password(password: str, confirmation: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirmation:
        raise ValueError("Passwords do not match.")


def validate_recovery_questions(questions: tuple[str, str, str], answers: tuple[str, str, str]) -> None:
    if any(question not in QUESTION_IDS for question in questions):
        raise ValueError("Select a valid predefined recovery question.")
    if len(set(questions)) != 3:
        raise ValueError("Recovery questions must be distinct.")
    if any(not answer.strip() for answer in answers):
        raise ValueError("All recovery answers are required.")


def create_public_user(
    username: str,
    password: str,
    confirmation: str,
    questions: tuple[str, str, str],
    answers: tuple[str, str, str],
):
    username = username.strip()
    if not username:
        raise ValueError("Username is required.")
    validate_password(password, confirmation)
    validate_recovery_questions(questions, answers)
    if repository.get_user_by_username(username) is not None:
        raise ValueError("That username is already in use.")
    return repository.create_user(
        username,
        db.hash_password(password),
        questions,
        tuple(hash_recovery_answer(answer) for answer in answers),
    )


def configure_recovery(user_id: int, current_password: str, questions: tuple[str, str, str], answers: tuple[str, str, str]) -> None:
    user = repository.get_user(user_id)
    if user is None or not db.verify_password(current_password, user["password_hash"]):
        raise ValueError("Current password is incorrect.")
    validate_recovery_questions(questions, answers)
    repository.update_recovery_configuration(
        user_id,
        questions,
        tuple(hash_recovery_answer(answer) for answer in answers),
    )


def verify_recovery_answers(user_id: int, answers: tuple[str, str, str]) -> bool:
    user = repository.get_user(user_id)
    if user is None or not user["is_active"] or not user["recovery_configured"]:
        return False
    return all(
        verify_recovery_answer(answer, user[f"recovery_answer_hash_{index}"] or "")
        for index, answer in enumerate(answers, 1)
    )


def reset_password(user_id: int, new_password: str, confirmation: str) -> None:
    validate_password(new_password, confirmation)
    db.update_user(user_id, password=new_password)
