"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : asr_provider.py
Purpose     : Base interface for all Automatic Speech Recognition providers.

Description:
    Defines the contract that every ASR provider must implement.

    Examples:
        • Faster Whisper
        • Whisper
        • Vosk
        • Bhashini
        • Custom ASR Providers

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
from ai.asr.models import (
    TranscriptionRequest,
    TranscriptionResult,
)


class ASRProvider(Provider):
    """
    Base interface for all ASR providers.

    Notes
    -----
    • Performs speech-to-text inference.
    • Does not manage model lifecycle.
    • Returns framework models only.
    """

    __slots__ = ()

    @abstractmethod
    def transcribe(
        self,
        request: TranscriptionRequest,
    ) -> TranscriptionResult:
        """
        Convert speech into text.

        Parameters
        ----------
        request : TranscriptionRequest
            Speech transcription request.

        Returns
        -------
        TranscriptionResult
            Provider-independent transcription result.

        Raises
        ------
        RuntimeError
            If transcription fails.
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
    def supports_language_detection(self) -> bool:
        """
        Indicates whether automatic language detection
        is supported.

        Returns
        -------
        bool
        """
        raise NotImplementedError