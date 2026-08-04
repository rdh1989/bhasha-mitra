"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : TTS Framework Data Models

Description:
    Defines provider-independent request and response models used by the
    Text-to-Speech module.

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
# Request Models
# ============================================================================

@dataclass(slots=True)
class SpeechRequest:
    """
    Text-to-Speech request.
    """

    text: str

    language: str

    voice: str

    output_path: Path


# ============================================================================
# Response Models
# ============================================================================

@dataclass(slots=True)
class SpeechResult:
    """
    Standard speech synthesis result returned by every TTS provider.
    """

    audio_path: Path

    language: str

    voice: str

    sample_rate: int

    duration: float | None = None