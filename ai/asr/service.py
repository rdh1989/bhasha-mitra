"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Automatic Speech Recognition Service

Description:
    Provides speech-to-text functionality using the configured ASR provider.

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

from app.ai.base.asr_provider import ASRProvider
from app.ai.asr.adapter import ASRAdapter


class ASRService:
    """
    ASR orchestration service.

    Responsibilities
    ----------------
    • Accept transcription requests.
    • Delegate inference to the configured provider.
    • Normalize provider output.
    • Return framework response objects.

    Notes
    -----
    This class contains no provider-specific logic.
    """

    def __init__(
        self,
        provider: ASRProvider,
        adapter: ASRAdapter,
    ) -> None:
        """
        Initialize ASR service.

        Parameters
        ----------
        provider : ASRProvider
            Configured ASR provider implementation.

        adapter : ASRAdapter
            Converts provider-specific output into framework models.
        """

        self._provider = provider
        self._adapter = adapter

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ):
        """
        Transcribe an audio file.

        Parameters
        ----------
        audio_path : str
            Audio file path.

        language : str | None
            Optional language hint.

        Returns
        -------
        Framework transcription result.
        """

        provider_result = self._provider.transcribe(
            audio_path=audio_path,
            language=language,
        )

        return self._adapter.to_framework_result(
            provider_result
        )

    def health_check(self) -> bool:
        """
        Verify provider health.
        """

        return self._provider.health_check()