"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Text-to-Speech Service

Description:
    Provides speech synthesis using the configured TTS provider.

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

from app.ai.base.tts_provider import TTSProvider
from app.ai.tts.adapter import TTSAdapter
from app.ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSService:
    """
    Text-to-Speech orchestration service.

    Responsibilities
    ----------------
    • Accept speech synthesis requests.
    • Delegate synthesis to the configured provider.
    • Normalize provider output.
    • Return framework models.
    """

    def __init__(
        self,
        provider: TTSProvider,
        adapter: TTSAdapter,
    ) -> None:
        self._provider = provider
        self._adapter = adapter

    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Convert text into speech.

        Parameters
        ----------
        request : SpeechRequest

        Returns
        -------
        SpeechResult
        """

        provider_result = self._provider.synthesize(
            text=request.text,
            language=request.language,
            voice=request.voice,
            output_path=request.output_path,
        )

        return self._adapter.to_framework_result(
            provider_result
        )

    def health_check(self) -> bool:
        """
        Check provider health.
        """

        return self._provider.health_check()