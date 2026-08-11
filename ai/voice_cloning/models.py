"""
===============================================================================
Bhasha Mitra - Voice Preserving Dubbing
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Voice-preserving dubbing contracts
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class VoiceDubbingRequest:
    """
    Request for voice-preserving dubbing.

    Required input:
        audio.wav
        translation.json
    """

    audio_path: Path
    translation_path: Path
    transcript_path: Path | None = None
    output_path: Path | None = None

    language: str = "mr"

    # IndicF5 works best with a clean speaker reference.
    reference_duration: float = 8.0

    # Generate one IndicF5 request per translation segment.
    # This gives us better timing control.
    segment_generation: bool = True

    # Allow small timing adjustment after generation.
    fit_to_original_duration: bool = False


@dataclass(slots=True)
class VoiceDubbingResult:
    audio_path: Path
    language: str
    sample_rate: int
    duration: float | None
    segments_generated: int