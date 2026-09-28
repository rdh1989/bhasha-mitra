from __future__ import annotations

RECOVERY_QUESTIONS = (
    {"id": "FIRST_SCHOOL", "text": "What was the name of your first school?"},
    {"id": "FIRST_PET", "text": "What was the name of your first pet?"},
    {"id": "CHILDHOOD_PLACE", "text": "What is your favorite childhood place?"},
    {"id": "FIRST_TEACHER", "text": "What was the name of your first teacher?"},
    {"id": "CHILDHOOD_NICKNAME", "text": "What was your childhood nickname?"},
    {"id": "CHILDHOOD_FRIEND", "text": "What is the name of a memorable childhood friend?"},
    {"id": "FAVORITE_SCHOOL_SUBJECT", "text": "What was your favorite subject in school?"},
    {"id": "BIRTH_CITY", "text": "What is the name of the city where you were born?"},
)

QUESTION_TEXT_BY_ID = {question["id"]: question["text"] for question in RECOVERY_QUESTIONS}
QUESTION_IDS = frozenset(QUESTION_TEXT_BY_ID)


def question_text(value: str) -> str:
    """Resolve a new ID or preserve an existing legacy free-text question."""
    return QUESTION_TEXT_BY_ID.get(value, value)
