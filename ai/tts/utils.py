"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : TTS Utility Functions

Description:
    Common helper functions used by the Text-to-Speech module.

These utilities are completely provider-independent.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
}


def normalize_language(language: str | None) -> str | None:
    """
    Normalize language code.

    Examples
    --------
    EN -> en
    mr-IN -> mr-in
    """

    if language is None:
        return None

    return language.strip().lower()


def normalize_voice(voice: str | None) -> str | None:
    """
    Normalize voice identifier.

    Examples
    --------
    Female -> female
    Medium -> medium
    """

    if voice is None:
        return None

    return voice.strip().lower()


def is_supported_audio(path: str | Path) -> bool:
    """
    Check whether the output audio format is supported.
    """

    extension = Path(path).suffix.lower()

    return extension in SUPPORTED_AUDIO_EXTENSIONS


def sanitize_text(text: str) -> str:
    """
    Remove unnecessary whitespace.
    """

    return " ".join(text.split())


def clamp_speed(speed: float) -> float:
    """
    Ensure speech speed stays within supported limits.

    Default framework limits:
        Minimum : 0.5
        Maximum : 2.0
    """

    return max(0.5, min(speed, 2.0))


def clamp_volume(volume: float) -> float:
    """
    Ensure volume stays within supported limits.

    Default framework limits:
        Minimum : 0.0
        Maximum : 2.0
    """

    return max(0.0, min(volume, 2.0))


def ensure_parent_directory(path: str | Path) -> Path:
    """
    Create parent directory if it does not exist.

    Returns
    -------
    Path
        Normalized output path.
    """

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_path