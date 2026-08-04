"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : constants.py
Purpose     : AI Framework Constants

Description:
    Defines framework-wide constants and enumerations used throughout
    the AI layer.

Design Notes:
    • Eliminates hard-coded strings.
    • Improves type safety.
    • Provides a single source of truth.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from enum import Enum


# ============================================================================
# Provider Categories
# ============================================================================

class ProviderCategory(str, Enum):
    """
    Supported AI provider categories.
    """

    ASR = "asr"

    TRANSLATION = "translation"

    TTS = "tts"

    LANGUAGE_DETECTION = "language_detection"

    SUBTITLE = "subtitle"


# ============================================================================
# Provider Status
# ============================================================================

class ProviderStatus(str, Enum):
    """
    Provider lifecycle status.
    """

    CREATED = "created"

    INITIALIZED = "initialized"

    READY = "ready"

    FAILED = "failed"

    SHUTDOWN = "shutdown"


# ============================================================================
# Model Status
# ============================================================================

class ModelStatus(str, Enum):
    """
    Model lifecycle status.
    """

    NOT_LOADED = "not_loaded"

    LOADING = "loading"

    LOADED = "loaded"

    FAILED = "failed"

    UNLOADED = "unloaded"


# ============================================================================
# Supported File Formats
# ============================================================================

SUPPORTED_AUDIO_EXTENSIONS = (
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
)

SUPPORTED_VIDEO_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
)

SUPPORTED_SUBTITLE_FORMATS = (
    "srt",
    "vtt",
)


# ============================================================================
# Default Languages
# ============================================================================

DEFAULT_SOURCE_LANGUAGE = "en"

DEFAULT_TARGET_LANGUAGE = "mr"