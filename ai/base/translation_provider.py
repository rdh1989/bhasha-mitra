"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : translation_provider.py
Purpose     : Base interface for all Translation providers.

Description:
    Defines the contract that every Translation provider must implement.

    Examples:
        • IndicTrans2
        • NLLB
        • Bhashini
        • Custom Translation Providers

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

from app.ai.base.provider import Provider
from app.ai.translation.models import (
    TranslationRequest,
    TranslationResult,
)


class TranslationProvider(Provider):
    """
    Base interface for all Translation providers.

    Notes
    -----
    • Performs language translation.
    • Does not manage model lifecycle.
    • Returns framework models only.
    """

    __slots__ = ()

    @abstractmethod
    def translate(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """
        Translate text between languages.

        Parameters
        ----------
        request : TranslationRequest
            Translation request.

        Returns
        -------
        TranslationResult
            Provider-independent translation result.
        """
        raise NotImplementedError

    @abstractmethod
    def supported_languages(self) -> list[str]:
        """
        Return supported language codes.

        Returns
        -------
        list[str]
        """
        raise NotImplementedError

    @abstractmethod
    def supports_auto_detection(self) -> bool:
        """
        Indicates whether automatic source language
        detection is supported.

        Returns
        -------
        bool
        """
        raise NotImplementedError