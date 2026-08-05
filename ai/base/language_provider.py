"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : language_provider.py
Purpose     : Base interface for all Language Detection providers.

Description:
    Defines the contract that every Language Detection provider must
    implement.

    Examples:
        • Lingua
        • FastText
        • Bhashini
        • Custom Language Detection Providers

Design Pattern:
    Strategy Pattern

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from abc import abstractmethod

from ai.base.provider import Provider
from ai.language_detection.models import (
    LanguageDetectionRequest,
    LanguageDetectionResult,
)


class LanguageProvider(Provider):
    """
    Base interface for all Language Detection providers.

    Notes
    -----
    • Performs language detection.
    • Does not manage model lifecycle.
    • Returns framework models only.
    """

    __slots__ = ()

    @abstractmethod
    def detect(
        self,
        request: LanguageDetectionRequest,
    ) -> LanguageDetectionResult:
        """
        Detect the language of the supplied input.

        Parameters
        ----------
        request : LanguageDetectionRequest
            Language detection request.

        Returns
        -------
        LanguageDetectionResult
            Provider-independent language detection result.
        """
        raise NotImplementedError

    @abstractmethod
    def supported_languages(self) -> list[str]:
        """
        Return the list of supported language codes.

        Returns
        -------
        list[str]
        """
        raise NotImplementedError

    @abstractmethod
    def supports_confidence_score(self) -> bool:
        """
        Indicates whether the provider returns confidence scores.

        Returns
        -------
        bool
        """
        raise NotImplementedError