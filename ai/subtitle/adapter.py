"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : Subtitle Adapter

Description:
    Converts provider-specific subtitle results into framework
    SubtitleResult objects.

Design Pattern:
    Adapter

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from typing import Any

from ai.subtitle.models import SubtitleResult


class SubtitleAdapter:
    """
    Converts provider-specific subtitle output into framework models.
    """

    def to_framework_result(
        self,
        provider_result: Any,
    ) -> SubtitleResult:
        """
        Convert provider output into framework result.

        Parameters
        ----------
        provider_result : Any
            Raw provider response.

        Returns
        -------
        SubtitleResult
        """

        if isinstance(provider_result, SubtitleResult):
            return provider_result

        raise NotImplementedError(
            "Provider result mapping has not been implemented."
        )