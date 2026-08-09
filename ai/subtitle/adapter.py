"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : Subtitle Provider Adapter

Description:
    Converts provider-specific subtitle results into the framework-standard
    SubtitleResult model.

Author:
    Bhasha Mitra AI Team
===============================================================================
"""

from __future__ import annotations

from ai.subtitle.models import SubtitleResult


class SubtitleAdapter:
    """
    Adapter for normalizing provider subtitle results.

    The adapter keeps provider-specific response structures isolated from
    the rest of the AI framework.
    """

    def to_framework_result(
        self,
        provider_result: SubtitleResult,
    ) -> SubtitleResult:
        """
        Convert provider result into framework result.

        Parameters
        ----------
        provider_result : SubtitleResult
            Result returned by the configured provider.

        Returns
        -------
        SubtitleResult
            Framework-standard result.
        """

        return SubtitleResult(
            subtitle_path=provider_result.subtitle_path,
            subtitle_format=provider_result.subtitle_format,
            segment_count=provider_result.segment_count,
        )