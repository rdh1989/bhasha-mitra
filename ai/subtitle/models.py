"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Subtitle Framework Data Models

Description:
    Defines provider-independent request and response models used by the
    Subtitle module.

    Subtitle generation works on generic timestamped text segments.
    The source of those segments may be ASR, translation, or any future
    processing component.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ============================================================================
# Word
# ============================================================================

@dataclass(slots=True)
class SubtitleWord:
    """
    Provider-independent word-level timing used to build rolling subtitle
    windows. Optional: callers without word timing simply omit it.
    """

    word: str

    start: float

    end: float


# ============================================================================
# Segment
# ============================================================================

@dataclass(slots=True)
class SubtitleSegment:
    """
    Provider-independent subtitle segment.

    Represents one timed piece of subtitle text.
    """

    start: float

    end: float

    text: str

    # Optional word-level timing for this segment. When present, the
    # subtitle service uses it to generate readable rolling subtitle
    # windows instead of showing the whole segment text for its entire
    # duration. When empty, generation falls back to the whole segment.
    words: list[SubtitleWord] = field(default_factory=list)


# ============================================================================
# Request Models
# ============================================================================

@dataclass(slots=True)
class SubtitleRequest:
    """
    Provider-independent subtitle generation request.
    """

    segments: list[SubtitleSegment]

    output_path: Path

    subtitle_format: str | None = None

    language: str | None = None


# ============================================================================
# Response Models
# ============================================================================

@dataclass(slots=True)
class SubtitleResult:
    """
    Standard subtitle generation result returned by every provider.
    """

    subtitle_path: Path

    subtitle_format: str

    segment_count: int
