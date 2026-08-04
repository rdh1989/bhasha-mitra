"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Subtitle Framework Data Models

Description:
    Defines provider-independent request and response models used by the
    Subtitle module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ai.asr.models import TranscriptionResult


# ============================================================================
# Request Models
# ============================================================================

@dataclass(slots=True)
class SubtitleRequest:
    """
    Subtitle generation request.
    """

    transcription: TranscriptionResult

    output_path: Path

    subtitle_format: str = "srt"


# ============================================================================
# Response Models
# ============================================================================

@dataclass(slots=True)
class SubtitleResult:
    """
    Standard subtitle generation result.
    """

    subtitle_path: Path

    subtitle_format: str

    segment_count: int