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

from dataclasses import dataclass
from pathlib import Path


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
