"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Language Detection Service

Description:
    Detects language using the configured language detection provider.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.language_detection.adapter import LanguageDetectionAdapter
from ai.language_detection.models import (
    LanguageDetectionRequest,
    LanguageDetectionResult,
)
from ai.model_manager.manager import ModelManager


class LanguageDetectionService:
    """
    Language Detection orchestration service.

    Responsibilities
    ----------------
    • Accept language detection requests.
    • Read provider metadata from ModelManager.
    • Initialize detector on demand.
    • Normalize provider output.
    """

    def __init__(
        self,
        adapter: LanguageDetectionAdapter,
    ) -> None:

        self._adapter = adapter
        self._model_manager = ModelManager()

    def detect(
        self,
        request: LanguageDetectionRequest,
    ) -> LanguageDetectionResult:
        """
        Detect language.
        """

        #
        # Language Detection is NOT preloaded.
        # Read provider configuration only.
        #
        metadata = self._model_manager.get_default_metadata(
            "language_detection"
        )

        #
        # TODO
        #
        # Initialize the detector using metadata.
        #
        # Example:
        #
        # provider = metadata["provider"]
        #
        # detector = ...
        #
        # provider_result = detector.detect(request.text)
        #
        # return self._adapter.to_framework_result(provider_result)
        #

        raise NotImplementedError(
            "Move language detection implementation here."
        )

    def health_check(
        self,
    ) -> bool:
        """
        Verify Language Detection configuration exists.
        """

        try:

            self._model_manager.get_default_metadata(
                "language_detection"
            )

            return True

        except Exception:

            return False