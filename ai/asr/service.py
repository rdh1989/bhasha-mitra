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

import time

from ai.asr.adapter import ASRAdapter
from ai.asr.config import ASRConfig
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
        self._config = ASRConfig()

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
        start_time = time.perf_counter()
        transcribe_kwargs = {
            "beam_size": self._config.beam_size,
            "best_of": self._config.best_of,
            "temperature": self._config.temperature,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "patience": 1.0,
            "without_timestamps": True,
        }

        if request.language or self._config.language:
            transcribe_kwargs["language"] = (
                request.language or self._config.language
            )

        segments, info = whisper.transcribe(
            request.audio_path,
            **transcribe_kwargs,
        )
        processing_time_seconds = round(
            time.perf_counter() - start_time,
            3,
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
        model_name = getattr(whisper, "model_name", None) or "medium"

        return ASRResult(
            provider="faster-whisper",
            model=model_name,
            transcript=" ".join(transcript).strip(),
            segments=framework_segments,
            detected_language=info.language,
            language_confidence=info.language_probability,
            processing_time_seconds=processing_time_seconds,
            metadata={
                "transcribe_kwargs": transcribe_kwargs,
            },
        )

    def health_check(self) -> bool:

        try:

            self._model_manager.get_default_model(
                "asr"
            )

            return True

        except Exception:

            return False