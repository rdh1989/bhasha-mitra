"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : tts_executor.py
Purpose     : Text-to-Speech Execution Engine

Description
-----------
Executes speech synthesis using the already loaded TTS model.

Responsibilities
----------------
• Retrieve loaded TTS model
• Execute inference
• Return framework models

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.execution.base_executor import BaseExecutor
from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSExecutor(BaseExecutor):
    """
    Executes Text-to-Speech synthesis.
    """

    CATEGORY = "tts"

    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Generate speech from text.
        """

        #
        # Retrieve loaded TTS model
        #
        tts_engine = self._model_manager.get_default_model(
            self.CATEGORY,
        )

        #
        # Execute synthesis
        #
        tts_engine.synthesize(
            text=request.text,
            output_path=str(request.output_path),
            voice=request.voice,
        )

        return SpeechResult(
            audio_path=request.output_path,
            language=request.language,
            voice=request.voice,
            sample_rate=22050,
            duration=None,
        )