"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Automatic Speech Recognition Service

Description:
    Provides speech-to-text functionality using loaded ASR models.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.asr.adapter import ASRAdapter
from ai.model_manager.manager import ModelManager


class ASRService:
    """
    ASR orchestration service.

    Responsibilities
    ----------------
    • Accept transcription requests.
    • Use already loaded ASR model.
    • Normalize framework response.
    """

    def __init__(
        self,
        adapter: ASRAdapter,
    ) -> None:

        self._adapter = adapter
        self._model_manager = ModelManager()

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ):
        """
        Transcribe audio.

        Parameters
        ----------
        audio_path : str

        language : str | None

        Returns
        -------
        Framework ASRResult
        """

        #
        # Get loaded ASR model
        #
        model = self._model_manager.get_default_model(
            "asr"
        )

        metadata = self._model_manager.get_default_metadata(
            "asr"
        )

        #
        # Move inference from your working
        # test_asr.py here.
        #

        raise NotImplementedError(
            "Move ASR inference from test_asr.py here."
        )

    def health_check(self) -> bool:
        """
        Verify ASR model is loaded.
        """

        try:

            self._model_manager.get_default_model(
                "asr"
            )

            return True

        except Exception:

            return False