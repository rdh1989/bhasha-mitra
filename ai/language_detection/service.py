"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Language Detection Service

Description:
    Detects the spoken or written language using the configured
    language detection provider.

Design Patterns:
    • Strategy
    • Dependency Injection

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.base.language_provider import LanguageProvider
# from ai.language_detection.adapter import LanguageAdapter
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
    • Delegate detection to the configured provider.
    • Normalize provider output.
    • Return framework models.
    """

    def __init__(
        self,
        provider: LanguageProvider,
        # adapter: LanguageAdapter,
    ) -> None:
        self._provider = provider
        # self._adapter = adapter

    def detect(
        self,
        request: LanguageDetectionRequest,
    ) -> LanguageDetectionResult:
        """
        Detect language.

        Parameters
        ----------
        request : LanguageDetectionRequest

        Returns
        -------
        LanguageDetectionResult
        """

        # provider_result = self._provider.detect(
        #     text=request.text,
        # )

        # return self._adapter.to_framework_result(
        #     provider_result
        # )
        return self._provider.detect(text=request.text,)

    def health_check(self) -> bool:
        """
        Verify provider health.
        """

        return self._provider.health_check()