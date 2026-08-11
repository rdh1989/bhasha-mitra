"""
Configuration for the optional voice-cloning module.

The existing ai.tts configuration is intentionally untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class VoiceCloningConfig:
    """
    Runtime configuration for IndicF5.

    model_path must point to a local IndicF5 model directory when
    running offline.
    """

    model_path: Path
    sample_rate: int = 24000
    speed: float = 1.0
    remove_silence: bool = False
    device: str = "auto"
