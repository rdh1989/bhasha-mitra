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