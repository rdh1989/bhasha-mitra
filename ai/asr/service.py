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

from httpcore import request

from ai.asr.adapter import ASRAdapter
from ai.model_manager.manager import ModelManager
from ai.asr.models import (
    ASRRequest,
    ASRResult,
    ASRSegment,
)

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
        request: ASRRequest,
    ) -> ASRResult:
        """
        Transcribe audio using the already loaded ASR model.
        """

        #
        # Get loaded Whisper model
        #
        whisper = self._model_manager.get_default_model(
            "asr"
        )

        #
        # Run transcription
        #
        segments, info = whisper.transcribe(
            request.audio_path,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        #
        # Convert framework segments
        #
        framework_segments = []

        transcript = []

        for idx, segment in enumerate(segments, start=1):

            transcript.append(segment.text)

            framework_segments.append(
                ASRSegment(
                    id=idx,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=None,
                )
            )

        #
        # Framework response
        #
        return ASRResult(
            provider="faster-whisper",
            model="medium",
            transcript=" ".join(transcript).strip(),
            segments=framework_segments,
            detected_language=info.language,
            language_confidence=info.language_probability,
        )

    def health_check(self) -> bool:

        try:

            self._model_manager.get_default_model(
                "asr"
            )

            return True

        except Exception:

            return False