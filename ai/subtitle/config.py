"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : Subtitle Configuration

Description:
    Defines provider-independent configuration for subtitle generation.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SubtitleConfig:
    """
    Configuration for subtitle generation.

    Notes
    -----
    This configuration contains only framework-level settings.
    Provider-specific implementation details must remain inside the
    configured subtitle provider.
    """

    # -------------------------------------------------------------------------
    # Subtitle Format
    # -------------------------------------------------------------------------

    subtitle_format: str = "srt"

    encoding: str = "utf-8"

    # -------------------------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------------------------

    include_timestamps: bool = True

    timestamp_precision: int = 3

    # -------------------------------------------------------------------------
    # Text Formatting
    # -------------------------------------------------------------------------

    max_characters_per_line: int = 42

    max_lines_per_subtitle: int = 2

    preserve_line_breaks: bool = True

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    overwrite_existing: bool = True

    verbose: bool = False