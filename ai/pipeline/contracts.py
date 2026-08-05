"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : contracts.py
Purpose     : Video Translation Pipeline Contracts

Description
-----------
Request and response models used by the Video Translation Pipeline.

These models are exchanged between the API layer and the Pipeline layer.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# -----------------------------------------------------------------------------
# AI-010 : Video Translation
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class VideoTranslationRequest:
    """
    Complete video translation request.
    """

    video_path: Path

    target_language: str

    generate_subtitles: bool = True

    generate_dubbing: bool = False


@dataclass(slots=True)
class VideoTranslationResult:
    """
    Complete video translation result.
    """

    translated_text: str

    subtitle_file: Path | None = None

    dubbed_audio: Path | None = None


# -----------------------------------------------------------------------------
# AI-011 : Transcript
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class VideoTranscriptRequest:
    """
    Transcript generation request.
    """

    video_path: Path


@dataclass(slots=True)
class VideoTranscriptResult:
    """
    Transcript generation result.
    """

    transcript: str


# -----------------------------------------------------------------------------
# AI-012 : Subtitle
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class VideoSubtitleRequest:
    """
    Subtitle generation request.
    """

    video_path: Path

    subtitle_format: str = "srt"


@dataclass(slots=True)
class VideoSubtitleResult:
    """
    Subtitle generation result.
    """

    subtitle_file: Path


# -----------------------------------------------------------------------------
# AI-013 : Dubbing
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class VideoDubbingRequest:
    """
    Video dubbing request.
    """

    video_path: Path

    target_language: str


@dataclass(slots=True)
class VideoDubbingResult:
    """
    Video dubbing result.
    """

    audio_file: Path