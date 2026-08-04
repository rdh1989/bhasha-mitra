"""
Faster-Whisper implementation of the ASR Provider.
"""

from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

from app.providers.asr.base_asr_provider import (
    BaseASRProvider,
)


class FasterWhisperProvider(BaseASRProvider):
    """
    Offline Speech-to-Text implementation.

    Uses Faster-Whisper running locally.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(
        self,
        audio_file: Path,
        language: str | None = None,
    ) -> str:
        """
        Convert speech to text.

        Args:
            audio_file:
                WAV/MP3 audio.

            language:
                Optional ISO language code.

        Returns:
            Complete transcript.
        """

        segments, _ = self._model.transcribe(
            str(audio_file),
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        transcript: list[str] = []

        for segment in segments:
            transcript.append(
                segment.text.strip()
            )

        return " ".join(transcript)

    def transcribe_segments(
        self,
        audio_file: Path,
        language: str | None = None,
    ) -> list[dict]:
        """
        Returns timestamped transcript.

        Example:

        [
            {
                "start":0.0,
                "end":2.5,
                "text":"Hello"
            }
        ]
        """

        segments, _ = self._model.transcribe(
            str(audio_file),
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        results: list[dict] = []

        for segment in segments:
            results.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
            )

        return results