"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Text-to-Speech Service

Description:
    Provides speech synthesis using the configured TTS provider.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.model_manager.manager import ModelManager
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
    • Read TTS configuration from ModelManager.
    • Initialize TTS engine on demand.
    • Normalize provider output.
    """

    def __init__(
        self,
        adapter: TTSAdapter,
    ) -> None:

        self._adapter = adapter
        self._model_manager = ModelManager()

    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Convert text into speech.
        """

        #
        # TTS is NOT preloaded.
        # Read provider configuration only.
        #
        metadata = self._model_manager.get_default_metadata(
            "tts"
        )

        #
        # TODO
        #
        # Initialize Piper (or configured provider)
        # using metadata.
        #
        # Example:
        #
        # provider = metadata["provider"]
        # voice_path = metadata["path"]
        #
        # provider_result = ...
        #
        # return self._adapter.to_framework_result(
        #     provider_result
        # )
        #

        raise NotImplementedError(
            "Move TTS inference from the working implementation."
        )

    def health_check(
        self,
    ) -> bool:
        """
        Verify TTS configuration exists.
        """

        try:

            self._model_manager.get_default_metadata(
                "tts"
            )

            return True

        except Exception:

            return False