"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : ASR-specific exceptions

Description:
    Defines all exceptions raised by the ASR module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.core.exceptions import AIFrameworkError


class ASRError(AIFrameworkError):
    """
    Base exception for all ASR-related errors.
    """
    pass


class TranscriptionError(ASRError):
    """
    Raised when speech transcription fails.
    """
    pass


class AudioFileNotFoundError(ASRError):
    """
    Raised when the input audio file cannot be found.
    """
    pass


class UnsupportedAudioFormatError(ASRError):
    """
    Raised when the input audio format is not supported.
    """
    pass


class EmptyAudioError(ASRError):
    """
    Raised when the audio file contains no detectable speech.
    """
    pass


class LanguageDetectionError(ASRError):
    """
    Raised when automatic language detection fails.
    """
    pass


class SegmentGenerationError(ASRError):
    """
    Raised when transcript segments cannot be generated.
    """
    pass


class ASRProviderError(ASRError):
    """
    Raised when the configured ASR provider reports an error.
    """
    pass