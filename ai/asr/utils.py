"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : ASR Utility Functions

Description:
    Common helper functions used by the ASR module.

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
    ".m4a",
}


def is_supported_audio(audio_path: str) -> bool:
    """
    Check whether an audio file format is supported.

    Parameters
    ----------
    audio_path : str

    Returns
    -------
    bool
    """

    extension = Path(audio_path).suffix.lower()

    return extension in SUPPORTED_AUDIO_EXTENSIONS


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds into HH:MM:SS.mmm format.

    Parameters
    ----------
    seconds : float

    Returns
    -------
    str
    """

    hours = int(seconds // 3600)

    minutes = int((seconds % 3600) // 60)

    secs = seconds % 60

    return f"{hours:02}:{minutes:02}:{secs:06.3f}"


def normalize_language(language: str | None) -> str | None:
    """
    Normalize language code.

    Examples
    --------
    EN -> en

    en-US -> en-us

    Parameters
    ----------
    language : str | None

    Returns
    -------
    str | None
    """

    if language is None:
        return None

    return language.strip().lower()


def sanitize_text(text: str) -> str:
    """
    Remove extra whitespace from transcript.

    Parameters
    ----------
    text : str

    Returns
    -------
    str
    """

    return " ".join(text.split())


def calculate_duration(
    start: float,
    end: float,
) -> float:
    """
    Calculate segment duration.

    Parameters
    ----------
    start : float

    end : float

    Returns
    -------
    float
    """

    return max(0.0, end - start)