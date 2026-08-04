"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : Language Detection Configuration

Description:
    Defines provider-independent configuration for the Language Detection
    module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LanguageDetectionConfig:
    """
    Configuration for Language Detection.

    Notes
    -----
    This configuration contains only framework-level settings.
    Provider-specific configuration must remain inside the provider
    implementation.
    """

    # -------------------------------------------------------------------------
    # Detection
    # -------------------------------------------------------------------------

    minimum_confidence: float = 0.50

    return_all_candidates: bool = True

    maximum_candidates: int = 5

    # -------------------------------------------------------------------------
    # Input
    # -------------------------------------------------------------------------

    normalize_text: bool = True

    ignore_case: bool = True

    remove_extra_whitespace: bool = True

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    timeout_seconds: int = 30

    verbose: bool = False