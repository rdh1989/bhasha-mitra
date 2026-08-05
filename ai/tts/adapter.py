"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : Text-to-Speech Adapter

Description:
    Converts provider-specific Text-to-Speech results into framework
    SpeechResult objects.

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

from ai.tts.models import SpeechResult


class TTSAdapter:
    """
    Converts provider-specific Text-to-Speech output into
    framework models.
    """

    def to_framework_result(
        self,
        provider_result: Any,
    ) -> SpeechResult:
        """
        Convert provider output into framework result.

        Parameters
        ----------
        provider_result : Any
            Raw provider response.

        Returns
        -------
        SpeechResult
        """

        if isinstance(provider_result, SpeechResult):
            return provider_result

        raise NotImplementedError(
            "Provider result mapping has not been implemented."
        )