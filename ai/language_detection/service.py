"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Language Detection Service
===============================================================================
"""

from __future__ import annotations

from lingua import LanguageDetectorBuilder

from ai.language_detection.adapter import LanguageDetectionAdapter
from ai.language_detection.models import (
    LanguageDetectionRequest,
    LanguageDetectionResult,
)


class LanguageDetectionService:
    """
    Language Detection orchestration service.

    Responsibilities
    ----------------
    • Accept language detection requests.
    • Detect language using the configured detection engine.
    • Return framework-standard result.
    """

    def __init__(
        self,
        adapter: LanguageDetectionAdapter,
    ) -> None:

        self._adapter = adapter

        self._detector = (
            LanguageDetectorBuilder
            .from_all_languages()
            .build()
        )

    # ------------------------------------------------------------------
    # Detect
    # ------------------------------------------------------------------

    def detect(
        self,
        request: LanguageDetectionRequest,
    ) -> LanguageDetectionResult:
        """
        Detect the language of supplied text.
        """

        text = request.text.strip()

        if not text:
            raise ValueError(
                "Text cannot be empty."
            )

        detected = (
            self._detector.detect_language_of(
                text
            )
        )

        if detected is None:
            raise RuntimeError(
                "Unable to detect language."
            )

        confidence = (
            self._detector.compute_language_confidence(
                text,
                detected,
            )
        )

        language_code = (
            detected.iso_code_639_1.name.lower()
        )

        language_name = detected.name.replace(
            "_",
            " ",
        ).title()

        return LanguageDetectionResult(
            provider="lingua",
            language=language_code,
            language_name=language_name,
            confidence=confidence,
            alternatives=[],
            metadata={
                "detector": "lingua",
            },
        )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Check language detection service health.
        """

        return self._detector is not None