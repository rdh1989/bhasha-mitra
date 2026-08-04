# """
# ===============================================================================
# Bhasha Mitra - AI Framework
# -------------------------------------------------------------------------------
# Module      : models.py
# Purpose     : Language Detection Framework Data Models

# Description:
#     Defines provider-independent request and response models used by the
#     Language Detection module.

# Author:
#     Bhasha Mitra AI Team

# Version:
#     1.0
# ===============================================================================
# """

# from __future__ import annotations

# from dataclasses import dataclass, field


# # ============================================================================
# # Request Models
# # ============================================================================

# @dataclass(slots=True)
# class LanguageDetectionRequest:
#     """
#     Language detection request.

#     The input may be plain text or an ASR transcript.
#     """

#     text: str


# # ============================================================================
# # Response Models
# # ============================================================================

# @dataclass(slots=True)
# class DetectedLanguage:
#     """
#     Represents one detected language.
#     """

#     language: str

#     confidence: float


# @dataclass(slots=True)
# class LanguageDetectionResult:
#     """
#     Standard language detection result returned by every provider.
#     """

#     primary_language: str

#     confidence: float

#     detected_languages: list[DetectedLanguage] = field(default_factory=list)



"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : Language Detection Models

Description:
    Common request/response models for all language detection providers.

Notes
-----
All language detection providers MUST use these models.

Supported Providers
-------------------
• Lingua
• FastText
• CLD3
• Bhashini
• Future Providers

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LanguageDetectionRequest:
    """
    Framework request passed to every Language Detection provider.
    """

    text: str

    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LanguageDetectionResult:
    """
    Standard framework response returned by every Language Detection provider.
    """

    # Provider Information
    provider: str

    # ISO-639-1 Language Code
    language: str

    # Human Readable Name
    language_name: str

    # Confidence (0.0 - 1.0)
    confidence: float

    # Optional alternatives
    alternatives: list[tuple[str, float]] = field(default_factory=list)

    # Provider specific metadata
    metadata: dict[str, Any] = field(default_factory=dict)