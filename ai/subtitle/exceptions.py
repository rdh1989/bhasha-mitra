"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : Subtitle-specific exceptions

Description:
    Defines all exceptions raised by the Subtitle module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from app.ai.core.exceptions import AIFrameworkError


class SubtitleError(AIFrameworkError):
    """
    Base exception for all subtitle-related errors.
    """
    pass


class SubtitleGenerationError(SubtitleError):
    """
    Raised when subtitle generation fails.
    """
    pass


class InvalidSubtitleFormatError(SubtitleError):
    """
    Raised when an unsupported subtitle format is requested.
    """
    pass


class EmptyTranscriptionError(SubtitleError):
    """
    Raised when subtitle generation is requested with an
    empty transcription.
    """
    pass


class SubtitleWriteError(SubtitleError):
    """
    Raised when the subtitle file cannot be written.
    """
    pass


class SubtitleProviderError(SubtitleError):
    """
    Raised when the configured subtitle provider
    reports an error.
    """
    pass


class SubtitleTimeoutError(SubtitleError):
    """
    Raised when subtitle generation exceeds the
    configured timeout.
    """
    pass