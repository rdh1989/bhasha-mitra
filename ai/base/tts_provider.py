"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Text-to-Speech Service
===============================================================================
"""

from __future__ import annotations

from ai.base.tts_provider import TTSProvider
from ai.tts.adapter import TTSAdapter
from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSService:
    """
    Text-to-Speech orchestration service.

    Responsibilities
    ----------------
    • Accept speech synthesis requests.
    • Delegate synthesis to the configured TTS provider.
    • Normalize provider output.
    • Remain completely vendor independent.
    """

    def __init__(
        self,
        provider: TTSProvider,
        adapter: TTSAdapter,
    ) -> None:

        self._provider = provider
        self._adapter = adapter

    # ------------------------------------------------------------------
    # Synthesize
    # ------------------------------------------------------------------

    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Convert text into speech using the configured provider.
        """

        if not request.text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        provider_result = (
            self._provider.synthesize(
                request
            )
        )

        return self._adapter.to_framework_result(
            provider_result
        )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Check provider health.
        """

        return self._provider.health_check()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """
        Shutdown provider.
        """

        self._provider.shutdown()