from __future__ import annotations

from pydantic import BaseModel


class RecoveryAnswers(BaseModel):
    answer_1: str
    answer_2: str
    answer_3: str


class RecoveryPassword(BaseModel):
    new_password: str
    confirm_password: str
