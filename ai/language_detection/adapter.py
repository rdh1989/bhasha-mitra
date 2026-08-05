"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : Language Detection Adapter

Description:
    Converts provider-specific language detection results into framework
    LanguageDetectionResult objects.

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

from ai.language_detection.models import (
    LanguageDetectionResult,
)


class LanguageDetectionAdapter:
    """
    Converts provider-specific language detection output into
    framework models.
    """

    def to_framework_result(
        self,
        provider_result: Any,
    ) -> LanguageDetectionResult:
        """
        Convert provider output into framework result.

        Parameters
        ----------
        provider_result : Any
            Raw provider response.

        Returns
        -------
        LanguageDetectionResult
        """

        if isinstance(provider_result, LanguageDetectionResult):
            return provider_result

        raise NotImplementedError(
            "Provider result mapping has not been implemented."
        )