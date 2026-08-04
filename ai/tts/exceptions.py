"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : TTS-specific exceptions

Description:
    Defines all exceptions raised by the Text-to-Speech module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from app.ai.core.exceptions import AIFrameworkError


class TTSError(AIFrameworkError):
    """
    Base exception for all Text-to-Speech related errors.
    """
    pass


class SpeechSynthesisError(TTSError):
    """
    Raised when speech synthesis fails.
    """
    pass


class EmptyTextError(TTSError):
    """
    Raised when synthesis is requested with empty text.
    """
    pass


class InvalidVoiceError(TTSError):
    """
    Raised when the requested voice is invalid.
    """
    pass


class UnsupportedVoiceError(TTSError):
    """
    Raised when the requested voice is not supported
    by the configured provider.
    """
    pass


class InvalidLanguageError(TTSError):
    """
    Raised when the requested language is invalid.
    """
    pass


class OutputFileError(TTSError):
    """
    Raised when the output audio file cannot be created.
    """
    pass


class TTSProviderError(TTSError):
    """
    Raised when the configured TTS provider reports an error.
    """
    pass


class SynthesisTimeoutError(TTSError):
    """
    Raised when speech synthesis exceeds the allowed timeout.
    """
    pass