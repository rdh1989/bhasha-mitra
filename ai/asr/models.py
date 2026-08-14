"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Common ASR Data Models

Description
-----------
Framework-standard models returned by every ASR provider.

These models are provider-agnostic and MUST NOT expose library-specific
objects (WhisperModel, Segment, Info, etc.).

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ASRWord:
    """
    Represents one word-level timestamp within a segment.
    """

    word: str

    start: float

    end: float

    confidence: float | None = None


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ASRSegment:
    """
    Represents one spoken segment.
    """

    id: int

    start: float

    end: float

    text: str

    confidence: float | None = None

    # Word-level timestamps, when the provider supports/enables them.
    # Empty when unavailable so downstream consumers can fall back to
    # segment-level timing without crashing.
    words: list[ASRWord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ASRResult:
    """
    Standard ASR output returned by every ASR provider.
    """

    # Provider information
    provider: str

    model: str

    # Transcript
    transcript: str

    segments: list[ASRSegment] = field(default_factory=list)

    # Language
    detected_language: str | None = None

    language_confidence: float | None = None

    # Processing
    duration_seconds: float | None = None

    processing_time_seconds: float | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Future extension
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ASRRequest:
    """
    Framework request passed to every ASR provider.
    """

    audio_path: str

    language: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)