"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : Translation-specific exceptions

Description:
    Defines all exceptions raised by the Translation module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from app.ai.core.exceptions import AIFrameworkError


class TranslationError(AIFrameworkError):
    """
    Base exception for all translation-related errors.
    """
    pass


class InvalidSourceLanguageError(TranslationError):
    """
    Raised when the source language is invalid or unsupported.
    """
    pass


class InvalidTargetLanguageError(TranslationError):
    """
    Raised when the target language is invalid or unsupported.
    """
    pass


class UnsupportedLanguagePairError(TranslationError):
    """
    Raised when the requested source-target language pair
    is not supported by the configured provider.
    """
    pass


class EmptyTextError(TranslationError):
    """
    Raised when translation is requested with empty text.
    """
    pass


class TranslationProviderError(TranslationError):
    """
    Raised when the configured translation provider
    returns an error.
    """
    pass


class TranslationTimeoutError(TranslationError):
    """
    Raised when translation exceeds the allowed timeout.
    """
    pass