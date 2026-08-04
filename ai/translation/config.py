"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : Translation Configuration

Description:
    Defines provider-independent configuration for the Translation module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranslationConfig:
    """
    Configuration for text translation.

    Notes
    -----
    This configuration contains framework-level options only.
    Provider-specific settings must remain inside the provider
    implementation.
    """

    # -------------------------------------------------------------------------
    # Language
    # -------------------------------------------------------------------------

    source_language: str = "en"

    target_language: str = "mr"

    auto_detect_source: bool = False

    # -------------------------------------------------------------------------
    # Translation Behaviour
    # -------------------------------------------------------------------------

    preserve_formatting: bool = True

    preserve_line_breaks: bool = True

    preserve_punctuation: bool = True

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    batch_size: int = 1

    timeout_seconds: int = 60

    verbose: bool = False