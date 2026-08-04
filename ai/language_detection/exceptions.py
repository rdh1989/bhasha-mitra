"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : Language Detection Exceptions

Description:
    Defines all exceptions raised by the Language Detection module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.core.exceptions import AIFrameworkError


class LanguageDetectionError(AIFrameworkError):
    """
    Base exception for all language detection errors.
    """
    pass


class EmptyInputError(LanguageDetectionError):
    """
    Raised when language detection is requested with empty input.
    """
    pass


class DetectionFailedError(LanguageDetectionError):
    """
    Raised when the provider fails to detect the language.
    """
    pass


class UnsupportedLanguageError(LanguageDetectionError):
    """
    Raised when the detected language is not supported by
    the application.
    """
    pass


class LowConfidenceError(LanguageDetectionError):
    """
    Raised when the detected language confidence is below
    the configured threshold.
    """
    pass


class LanguageProviderError(LanguageDetectionError):
    """
    Raised when the configured language detection provider
    reports an error.
    """
    pass


class DetectionTimeoutError(LanguageDetectionError):
    """
    Raised when language detection exceeds the allowed timeout.
    """
    pass