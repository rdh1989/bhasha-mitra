"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : TTS Configuration

Description:
    Defines provider-independent configuration for the Text-to-Speech module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TTSConfig:
    """
    Configuration for Text-to-Speech.

    Notes
    -----
    This configuration contains framework-level settings only.
    Provider-specific options should remain inside the provider
    implementation.
    """

    # -------------------------------------------------------------------------
    # Language
    # -------------------------------------------------------------------------

    language: str = "mr"

    voice: str = "default"

    # -------------------------------------------------------------------------
    # Audio
    # -------------------------------------------------------------------------

    sample_rate: int = 22050

    volume: float = 1.0

    speed: float = 1.0

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    overwrite_output: bool = True

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    timeout_seconds: int = 60

    verbose: bool = False