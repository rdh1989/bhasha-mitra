"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : asr_executor.py
Purpose     : ASR Execution Engine

Description
-----------
Executes speech recognition using the already loaded ASR model.

Responsibilities
----------------
• Retrieve loaded ASR model
• Execute speech recognition
• Convert provider output into framework models

Notes
-----
Models are loaded once during application startup by ModelManager.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.execution.base_executor import BaseExecutor
from ai.asr.models import (
    ASRResult,
    ASRSegment,
)


class ASRExecutor(BaseExecutor):
    """
    Executes Automatic Speech Recognition.
    """

    CATEGORY = "asr"

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> ASRResult:
        """
        Execute speech recognition.
        """

        #
        # Retrieve loaded Whisper model
        #
        whisper_model = self._model_manager.get_default_model(
            self.CATEGORY,
        )

        #
        # Run inference
        #
        segments, info = whisper_model.transcribe(
            audio=audio_path,
            language=language,
            beam_size=5,
        )

        framework_segments: list[ASRSegment] = []

        transcript_parts: list[str] = []

        for index, segment in enumerate(segments):

            transcript_parts.append(segment.text)

            framework_segments.append(
                ASRSegment(
                    id=index,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    confidence=None,
                )
            )

        return ASRResult(
            provider="faster_whisper",
            model=self._model_manager.get_default_model_name(
                self.CATEGORY,
            ),
            transcript="".join(transcript_parts).strip(),
            segments=framework_segments,
            detected_language=info.language,
            language_confidence=info.language_probability,
        )