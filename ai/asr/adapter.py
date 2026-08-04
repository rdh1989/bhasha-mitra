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

from app.ai.asr.models import (
    LanguageInfo,
    Segment,
    TranscriptionResult,
)


class ASRAdapter:
    """
    Adapter responsible for converting provider-specific transcription
    results into framework models.

    Notes
    -----
    This class isolates the framework from provider-specific SDKs.
    Every ASR provider must return a TranscriptionResult before the
    response leaves the AI layer.
    """

    def to_framework_result(
        self,
        provider_result: Any,
    ) -> TranscriptionResult:
        """
        Convert a provider-specific result into a framework result.

        Parameters
        ----------
        provider_result : Any
            Raw object returned by the configured provider.

        Returns
        -------
        TranscriptionResult

        Raises
        ------
        NotImplementedError
            Raised until a provider-specific mapper is implemented.
        """

        if isinstance(provider_result, TranscriptionResult):
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
    ) -> Segment:
        """
        Create a framework Segment object.
        """

        return Segment(
            id=segment_id,
            start=start,
            end=end,
            text=text,
            confidence=confidence,
        )

    @staticmethod
    def create_language(
        *,
        language: str,
        probability: float,
    ) -> LanguageInfo:
        """
        Create a framework LanguageInfo object.
        """

        return LanguageInfo(
            language=language,
            probability=probability,
        )