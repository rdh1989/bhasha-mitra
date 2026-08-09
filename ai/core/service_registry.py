"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service_registry.py
Purpose     : AI Service Registry

Description:
    Constructs framework services.

Responsibilities:
    • Build service instances
    • Inject adapters
    • Keep provider/model resolution inside services

Notes:
    Model loading is handled by ModelManager.
    Services obtain configured/loaded implementations through the framework.

Author:
    Bhasha Mitra AI Team
===============================================================================
"""

from __future__ import annotations

from ai.translation.service import TranslationService
from ai.translation.adapter import TranslationAdapter

from ai.asr.service import ASRService
from ai.asr.adapter import ASRAdapter

from ai.language_detection.service import (
    LanguageDetectionService,
)
from ai.language_detection.adapter import (
    LanguageDetectionAdapter,
)

from ai.tts.service import TTSService
from ai.tts.adapter import TTSAdapter

from ai.subtitle.service import SubtitleService
from ai.subtitle.adapter import SubtitleAdapter


class ServiceRegistry:
    """
    Creates AI service instances.

    Services are provider-agnostic.

    Provider/model resolution is handled internally by the respective
    service and framework model-management layer.
    """

    # -------------------------------------------------------------------------
    # Translation
    # -------------------------------------------------------------------------

    @staticmethod
    def translation_service() -> TranslationService:

        return TranslationService(
            adapter=TranslationAdapter(),
        )

    # -------------------------------------------------------------------------
    # ASR
    # -------------------------------------------------------------------------

    @staticmethod
    def asr_service() -> ASRService:

        return ASRService(
            adapter=ASRAdapter(),
        )

    # -------------------------------------------------------------------------
    # Language Detection
    # -------------------------------------------------------------------------

    @staticmethod
    def language_detection_service() -> LanguageDetectionService:

        return LanguageDetectionService(
            adapter=LanguageDetectionAdapter(),
        )

    # -------------------------------------------------------------------------
    # Text-To-Speech
    # -------------------------------------------------------------------------

    @staticmethod
    def tts_service() -> TTSService:

        return TTSService(
            adapter=TTSAdapter(),
        )

    # -------------------------------------------------------------------------
    # Subtitle
    # -------------------------------------------------------------------------

    @staticmethod
    def subtitle_service() -> SubtitleService:

        return SubtitleService(
            adapter=SubtitleAdapter(),
        )
