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

import math
import time

from ai.asr.adapter import ASRAdapter
from ai.asr.config import ASRConfig
from ai.model_manager.manager import ModelManager
from ai.asr.models import (
    ASRRequest,
    ASRResult,
    ASRSegment,
    ASRWord,
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
            "word_timestamps": self._config.enable_word_timestamps,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "patience": 1.0,
            # Must stay False so Faster-Whisper emits real ASR time-aligned
            # speech segments rather than text-only output.
            "without_timestamps": False,
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
                    words=self._extract_words(segment),
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

    @staticmethod
    def _extract_words(
        provider_segment,
    ) -> list[ASRWord]:
        """
        Convert Faster-Whisper word timestamps into framework ASRWord
        models. Faster-Whisper-specific objects must never leak past this
        point.

        Returns an empty list whenever word timestamps are unavailable or
        malformed, so callers can gracefully fall back to segment-level
        timing instead of crashing.
        """

        raw_words = getattr(provider_segment, "words", None) or []

        words: list[ASRWord] = []

        for raw_word in raw_words:

            text = str(getattr(raw_word, "word", "") or "").strip()

            if not text:
                continue

            start = getattr(raw_word, "start", None)
            end = getattr(raw_word, "end", None)

            if start is None or end is None:
                continue

            try:
                start = float(start)
                end = float(end)
            except (TypeError, ValueError):
                continue

            if not (math.isfinite(start) and math.isfinite(end)):
                continue

            if end < start:
                start, end = end, start

            probability = getattr(raw_word, "probability", None)

            words.append(
                ASRWord(
                    word=text,
                    start=start,
                    end=end,
                    confidence=(
                        float(probability)
                        if probability is not None
                        else None
                    ),
                )
            )

        return words

    def health_check(self) -> bool:

        try:

            self._model_manager.get_default_model(
                "asr"
            )

            return True

        except Exception:

            return False