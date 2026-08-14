"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : ASR Configuration

Description:
    Defines configuration settings for the ASR module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ASRConfig:
    """
    Configuration for Automatic Speech Recognition.

    Notes
    -----
    This configuration is provider-independent and contains only
    framework-level settings. Provider-specific implementations are
    responsible for interpreting the applicable options.
    """

    # -------------------------------------------------------------------------
    # Language
    # -------------------------------------------------------------------------

    language: str | None = None

    auto_detect_language: bool = True

    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------

    beam_size: int = 5

    best_of: int = 5

    temperature: float = 0.0

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    enable_word_timestamps: bool = True

    enable_segment_timestamps: bool = True

    return_confidence: bool = True

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------

    batch_size: int = 1

    cpu_threads: int = 4

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    verbose: bool = False