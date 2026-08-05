"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : tts_provider.py
Purpose     : Base interface for all Text-to-Speech providers.

Description:
    Defines the contract that every TTS provider must implement.

    Examples:
        • Piper
        • Coqui TTS
        • Bhashini
        • Custom TTS Providers

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
from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSProvider(Provider):
    """
    Base interface for all Text-to-Speech providers.

    Notes
    -----
    • Performs speech synthesis.
    • Does not manage model lifecycle.
    • Returns framework models only.
    """

    __slots__ = ()

    @abstractmethod
    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Convert text into speech.

        Parameters
        ----------
        request : SpeechRequest
            Speech synthesis request.

        Returns
        -------
        SpeechResult
            Provider-independent speech synthesis result.
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
    def available_voices(
        self,
        language: str | None = None,
    ) -> list[str]:
        """
        Return available voices.

        Parameters
        ----------
        language : str | None
            Optional language filter.

        Returns
        -------
        list[str]
        """
        raise NotImplementedError