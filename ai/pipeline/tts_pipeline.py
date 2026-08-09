"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : tts_pipeline.py
Purpose     : Text-to-Speech Pipeline
===============================================================================
"""

from __future__ import annotations

from ai.core.service_registry import ServiceRegistry
from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSPipeline:
    """
    Text-to-Speech pipeline.

    Flow
    ----
    Text
        ↓
    TTS Service
        ↓
    Audio
    """

    def __init__(self) -> None:

        self._tts_service = (
            ServiceRegistry.tts_service()
        )

    def execute(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Execute TTS pipeline.
        """

        return self._tts_service.synthesize(
            request
        )

    def health_check(self) -> bool:
        """
        Check TTS pipeline health.
        """

        return self._tts_service.health_check()