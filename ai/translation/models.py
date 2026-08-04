"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Translation Framework Data Models

Description:
    Defines provider-independent request and response models used by the
    Translation module.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================================
# Request Models
# ============================================================================

@dataclass(slots=True)
class TranslationRequest:
    """
    Translation request.
    """

    text: str

    source_language: str

    target_language: str


# ============================================================================
# Response Models
# ============================================================================

@dataclass(slots=True)
class TranslationResult:
    """
    Standard translation result returned by every translation provider.
    """

    original_text: str

    translated_text: str

    source_language: str

    target_language: str

    confidence: float | None = None