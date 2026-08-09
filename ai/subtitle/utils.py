"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : Subtitle Utilities

Description:
    Utility functions used by subtitle providers.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations


def seconds_to_srt_time(
    seconds: float,
) -> str:
    """
    Convert seconds into SRT timestamp.

    Example
    -------
    65.349

    →

    00:01:05,349
    """

    milliseconds = int(round(seconds * 1000))

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    secs = milliseconds // 1000
    milliseconds %= 1000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )