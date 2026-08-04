"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : Subtitle Utility Functions

Description:
    Common helper functions used by the Subtitle module.

These utilities are completely provider-independent.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path


SUPPORTED_SUBTITLE_FORMATS = {
    "srt",
    "vtt",
}


def normalize_format(subtitle_format: str | None) -> str | None:
    """
    Normalize subtitle format.

    Examples
    --------
    SRT -> srt
    VTT -> vtt
    """

    if subtitle_format is None:
        return None

    return subtitle_format.strip().lower()


def is_supported_format(subtitle_format: str) -> bool:
    """
    Check whether subtitle format is supported.

    Parameters
    ----------
    subtitle_format : str

    Returns
    -------
    bool
    """

    return normalize_format(subtitle_format) in SUPPORTED_SUBTITLE_FORMATS


def ensure_output_directory(path: str | Path) -> Path:
    """
    Create parent directory if required.

    Parameters
    ----------
    path : str | Path

    Returns
    -------
    Path
    """

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_path


def sanitize_text(text: str) -> str:
    """
    Remove unnecessary whitespace.

    Parameters
    ----------
    text : str

    Returns
    -------
    str
    """

    return " ".join(text.split())


def clamp_line_length(
    text: str,
    max_length: int,
) -> list[str]:
    """
    Split subtitle text into multiple lines.

    Parameters
    ----------
    text : str

    max_length : int

    Returns
    -------
    list[str]
    """

    words = text.split()

    if not words:
        return []

    lines = []
    current = []

    for word in words:

        candidate = " ".join(current + [word])

        if len(candidate) <= max_length:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return lines


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format.

    Example
    -------
    65.250

    →

    00:01:05,250
    """

    hours = int(seconds // 3600)

    minutes = int((seconds % 3600) // 60)

    secs = int(seconds % 60)

    milliseconds = int(round((seconds - int(seconds)) * 1000))

    return (
        f"{hours:02}:"
        f"{minutes:02}:"
        f"{secs:02},"
        f"{milliseconds:03}"
    )