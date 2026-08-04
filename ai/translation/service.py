"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Translation Service

Description:
    Provides text translation using the configured Translation provider.

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

from ai.base.translation_provider import TranslationProvider
from ai.translation.adapter import TranslationAdapter
from ai.translation.models import (
    TranslationRequest,
    TranslationResult,
)


class TranslationService:
    """
    Translation orchestration service.

    Responsibilities
    ----------------
    • Accept translation requests.
    • Delegate translation to configured provider.
    • Normalize provider output.
    • Return framework models.
    """

    def __init__(
        self,
        provider: TranslationProvider,
        adapter: TranslationAdapter,
    ) -> None:
        self._provider = provider
        self._adapter = adapter

    def translate(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """
        Translate text.

        Parameters
        ----------
        request : TranslationRequest

        Returns
        -------
        TranslationResult
        """

        provider_result = self._provider.translate(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
        )

        return self._adapter.to_framework_result(
            provider_result
        )

    def health_check(self) -> bool:
        """
        Check provider health.
        """

        return self._provider.health_check()