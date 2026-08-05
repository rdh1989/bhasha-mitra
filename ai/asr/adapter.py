"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : ASR Adapter

Description:
    Converts provider-specific ASR results into framework models.

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

from ai.asr.models import (
    ASRResult,
    ASRSegment,
)


class ASRAdapter:
    """
    Adapter responsible for converting provider-specific transcription
    results into framework models.
    """

    def to_framework_result(
        self,
        provider_result: Any,
    ) -> ASRResult:
        """
        Convert provider-specific result into framework result.
        """

        if isinstance(provider_result, ASRResult):
            return provider_result

        raise NotImplementedError(
            "Provider result mapping has not been implemented."
        )

    @staticmethod
    def create_segment(
        *,
        segment_id: int,
        start: float,
        end: float,
        text: str,
        confidence: float | None = None,
    ) -> ASRSegment:
        """
        Create framework ASR segment.
        """

        return ASRSegment(
            id=segment_id,
            start=start,
            end=end,
            text=text,
            confidence=confidence,
        )