"""Builds the natural-language "description" style prompt for Indic Parler-TTS."""
from __future__ import annotations

from app.config import Language

_DEFAULT_STYLE = (
    "a clear, natural, and moderately paced voice. The recording is of very "
    "high quality with no background noise"
)


def build_description(language: Language, voice_index: int = 0) -> str:
    if language.tts_speakers:
        speaker = language.tts_speakers[voice_index % len(language.tts_speakers)]
        return f"{speaker} speaks in {_DEFAULT_STYLE}."
    return f"A speaker delivers speech in {_DEFAULT_STYLE}."
