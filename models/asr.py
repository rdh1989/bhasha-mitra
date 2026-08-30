"""Thread-safe faster-whisper ASR wrapper (CPU, CTranslate2)."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    segments: list[Segment]
    language: str
    language_probability: float


class ASREngine:
    """Loads a single faster-whisper model lazily and reuses it for all jobs.

    num_workers > 1 lets CTranslate2 safely serve that many concurrent
    transcribe() calls on this one loaded model, which is what allows
    multiple jobs to run in parallel without reloading or fighting over it.
    """

    def __init__(self, model_dir, compute_type: str = "int8", cpu_threads: int = 4, num_workers: int = 1):
        self._model_dir = str(model_dir)
        self._compute_type = compute_type
        self._cpu_threads = cpu_threads
        self._num_workers = max(1, num_workers)
        self._model = None
        self._lock = threading.Lock()

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            logger.info(
                "Loading faster-whisper ASR model from %s (compute_type=%s, num_workers=%d)",
                self._model_dir, self._compute_type, self._num_workers,
            )
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self._model_dir,
                    device="cpu",
                    compute_type=self._compute_type,
                    cpu_threads=self._cpu_threads,
                    num_workers=self._num_workers,
                )
            except Exception:
                logger.exception("Failed to load ASR model from %s", self._model_dir)
                raise
            logger.info("ASR model loaded successfully")

    def unload(self) -> None:
        """Release the model so its (native CTranslate2) memory can be freed."""
        with self._lock:
            if self._model is None:
                return
            self._model = None
        logger.info("ASR model unloaded")

    def transcribe(
        self,
        audio_path: str,
        task: str = "transcribe",
        language: str | None = None,
        progress_cb=None,
    ) -> TranscriptionResult:
        """Run ASR. task is "transcribe" (source language text) or
        "translate" (Whisper's built-in X-to-English translation)."""
        self.ensure_loaded()
        logger.debug("Transcribing %s (task=%s, language=%s)", audio_path, task, language)
        try:
            segments_iter, info = self._model.transcribe(
                audio_path,
                task=task,
                language=language,
                vad_filter=True,
                beam_size=5,
                word_timestamps=False,
            )
            segments: list[Segment] = []
            total_duration = info.duration or 0.0
            for seg in segments_iter:
                text = seg.text.strip()
                if text:
                    segments.append(Segment(start=seg.start, end=seg.end, text=text))
                if progress_cb and total_duration > 0:
                    progress_cb(min(seg.end / total_duration, 1.0))
        except Exception:
            logger.exception("ASR transcription failed for %s (task=%s)", audio_path, task)
            raise
        logger.info(
            "Transcription done: task=%s language=%s segments=%d",
            task, info.language, len(segments),
        )
        return TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
        )
