"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : language_detection_executor.py
Purpose     : Language Detection Execution Engine

Description
-----------
Executes language detection using the already loaded language detection model.

Responsibilities
----------------
• Retrieve loaded model
• Execute inference
• Return framework models

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.execution.base_executor import BaseExecutor
from ai.language_detection.models import (
    LanguageDetectionRequest,
    LanguageDetectionResult,
)


class LanguageDetectionExecutor(BaseExecutor):
    """
    Executes language detection.
    """

    CATEGORY = "language_detection"

    def detect(
        self,
        request: LanguageDetectionRequest,
    ) -> LanguageDetectionResult:
        """
        Detect language.
        """

        #
        # Retrieve loaded detector
        #
        detector = self._model_manager.get_default_model(
            self.CATEGORY,
        )

        #
        # Execute detection
        #
        result = detector.detect_language_of(
            request.text,
        )

        #
        # Build framework response
        #
        return LanguageDetectionResult(
            provider="lingua",
            language=result.iso_code_639_1.name.lower(),
            language_name=result.name.title(),
            confidence=1.0,
            alternatives=[],
            metadata={},
        )