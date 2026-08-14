"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : transcript_pipeline.py
Purpose     : AI Transcript Pipeline

Description:
    Generates a timestamped transcript from an audio file.

Pipeline
--------
Audio
    ↓
Chunk Long Audio
    ↓
ASR
    ↓
Merge Transcript Segments
    ↓
transcript.json

The Backend team is responsible for:
    • Providing the audio file

This pipeline is responsible for:
    • Long-audio handling
    • Audio chunking
    • ASR orchestration
    • Timestamp correction
    • Transcript merging
    • Persisting timestamped transcript

This pipeline does NOT:
    • Translate text
    • Extract audio from video
    • Process video
    • Run FFmpeg
    • Generate subtitles
    • Generate TTS audio
    • Merge media

Author:
    Bhasha Mitra AI Team

Version:
    1.2
===============================================================================
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

from ai.asr.models import (
    ASRRequest,
    ASRResult,
    ASRSegment,
    ASRWord,
)
from ai.core.service_registry import ServiceRegistry

from ai.pipeline.contracts import (
    VideoTranscriptRequest,
    VideoTranscriptResult,
)


class TranscriptPipeline:

    DEFAULT_CHUNK_DURATION_SECONDS = 30 * 60

    def __init__(
        self,
        chunk_duration_seconds: int = DEFAULT_CHUNK_DURATION_SECONDS,
    ) -> None:

        if chunk_duration_seconds <= 0:
            raise ValueError(
                "chunk_duration_seconds must be greater than zero."
            )

        self._chunk_duration_seconds = (
            chunk_duration_seconds
        )

        self._asr_service = (
            ServiceRegistry.asr_service()
        )

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(
        self,
        request: VideoTranscriptRequest,
    ) -> VideoTranscriptResult:

        audio_path = Path(
            request.audio_path
        )

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        if not audio_path.is_file():
            raise ValueError(
                f"Audio path is not a file: {audio_path}"
            )

        duration = self._get_audio_duration(
            audio_path
        )

        # --------------------------------------------------------------
        # Short audio
        # --------------------------------------------------------------

        if duration <= self._chunk_duration_seconds:

            transcription = self._transcribe(
                audio_path
            )

        # --------------------------------------------------------------
        # Long audio
        # --------------------------------------------------------------

        else:

            chunk_directory = (
                audio_path.parent
                / f".{audio_path.stem}_transcript_chunks"
            )

            chunk_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            try:

                chunk_files = self._split_audio(
                    audio_path=audio_path,
                    output_directory=chunk_directory,
                )

                transcription = (
                    self._transcribe_chunks(
                        chunk_files
                    )
                )

            finally:

                self._cleanup_chunks(
                    chunk_directory
                )

        # --------------------------------------------------------------
        # Save timestamped transcript
        # --------------------------------------------------------------

        transcript_path = (
            audio_path.parent
            / "transcript.json"
        )

        self._save_transcript(
            transcription=transcription,
            output_path=transcript_path,
        )

        # --------------------------------------------------------------
        # Return transcript artifact
        # --------------------------------------------------------------

        return VideoTranscriptResult(
            transcript_path=transcript_path
        )

    # ------------------------------------------------------------------
    # ASR
    # ------------------------------------------------------------------

    def _transcribe(
        self,
        audio_path: Path,
    ) -> ASRResult:

        asr_request = ASRRequest(
            audio_path=str(audio_path),
        )

        return self._asr_service.transcribe(
            asr_request
        )

    # ------------------------------------------------------------------
    # Transcribe Chunks
    # ------------------------------------------------------------------

    def _transcribe_chunks(
        self,
        chunk_files: list[tuple[Path, float]],
    ) -> ASRResult:

        all_segments: list[ASRSegment] = []
        transcript_parts: list[str] = []

        detected_language: str | None = None
        language_confidence: float | None = None

        provider = ""
        model = ""

        total_duration = 0.0
        segment_id = 1

        for chunk_path, offset_seconds in chunk_files:

            result = self._transcribe(
                chunk_path
            )

            provider = result.provider
            model = result.model

            if detected_language is None:
                detected_language = (
                    result.detected_language
                )

            if language_confidence is None:
                language_confidence = (
                    result.language_confidence
                )

            if result.transcript.strip():

                transcript_parts.append(
                    result.transcript.strip()
                )

            for segment in result.segments:

                all_segments.append(
                    ASRSegment(
                        id=segment_id,
                        start=(
                            segment.start
                            + offset_seconds
                        ),
                        end=(
                            segment.end
                            + offset_seconds
                        ),
                        text=segment.text.strip(),
                        confidence=segment.confidence,
                        words=[
                            ASRWord(
                                word=word.word,
                                start=word.start + offset_seconds,
                                end=word.end + offset_seconds,
                                confidence=word.confidence,
                            )
                            for word in segment.words
                        ],
                    )
                )

                segment_id += 1

            if result.duration_seconds is not None:

                total_duration += (
                    result.duration_seconds
                )

        return ASRResult(
            provider=provider,
            model=model,
            transcript=" ".join(
                transcript_parts
            ).strip(),
            segments=all_segments,
            detected_language=detected_language,
            language_confidence=language_confidence,
            duration_seconds=(
                total_duration
                if total_duration > 0
                else None
            ),
            metadata={
                "chunked": True,
                "chunk_duration_seconds": (
                    self._chunk_duration_seconds
                ),
                "chunk_count": len(
                    chunk_files
                ),
            },
        )

    # ------------------------------------------------------------------
    # Save Transcript
    # ------------------------------------------------------------------

    def _save_transcript(
        self,
        transcription: ASRResult,
        output_path: Path,
    ) -> None:
        """
        Persist timestamped transcript data.

        The text field contains the original ASR text.
        Timing metadata is preserved for downstream
        translation/subtitle processing.
        """

        transcript_data = {
            "segments": [
                {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "confidence": word.confidence,
                        }
                        for word in segment.words
                    ],
                }
                for segment in transcription.segments
            ]
        }

        output_path.write_text(
            json.dumps(
                transcript_data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Audio Duration
    # ------------------------------------------------------------------

    def _get_audio_duration(
        self,
        audio_path: Path,
    ) -> float:

        try:

            with wave.open(
                str(audio_path),
                "rb",
            ) as audio:

                frame_rate = (
                    audio.getframerate()
                )

                frame_count = (
                    audio.getnframes()
                )

                if frame_rate <= 0:
                    raise ValueError(
                        "Invalid audio sample rate."
                    )

                return (
                    frame_count / frame_rate
                )

        except wave.Error as exc:

            raise ValueError(
                "Unable to read audio duration."
            ) from exc

    # ------------------------------------------------------------------
    # Audio Splitting
    # ------------------------------------------------------------------

    def _split_audio(
        self,
        audio_path: Path,
        output_directory: Path,
    ) -> list[tuple[Path, float]]:

        chunk_files: list[
            tuple[Path, float]
        ] = []

        with wave.open(
            str(audio_path),
            "rb",
        ) as source:

            frame_rate = (
                source.getframerate()
            )

            channels = (
                source.getnchannels()
            )

            sample_width = (
                source.getsampwidth()
            )

            chunk_frames = int(
                frame_rate
                * self._chunk_duration_seconds
            )

            if chunk_frames <= 0:
                raise ValueError(
                    "Invalid chunk duration."
                )

            chunk_index = 1
            offset_seconds = 0.0

            while True:

                frames = source.readframes(
                    chunk_frames
                )

                if not frames:
                    break

                chunk_path = (
                    output_directory
                    / f"chunk_{chunk_index:05d}.wav"
                )

                with wave.open(
                    str(chunk_path),
                    "wb",
                ) as chunk:

                    chunk.setnchannels(
                        channels
                    )

                    chunk.setsampwidth(
                        sample_width
                    )

                    chunk.setframerate(
                        frame_rate
                    )

                    chunk.writeframes(
                        frames
                    )

                frame_count = (
                    len(frames)
                    // sample_width
                    // channels
                )

                chunk_duration = (
                    frame_count / frame_rate
                )

                chunk_files.append(
                    (
                        chunk_path,
                        offset_seconds,
                    )
                )

                offset_seconds += (
                    chunk_duration
                )

                chunk_index += 1

        return chunk_files

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_chunks(
        self,
        chunk_directory: Path,
    ) -> None:

        if not chunk_directory.exists():
            return

        for file_path in chunk_directory.iterdir():

            try:

                if file_path.is_file():
                    file_path.unlink()

            except OSError:
                pass

        try:
            chunk_directory.rmdir()

        except OSError:
            pass

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(
        self,
    ) -> bool:

        return self._asr_service.health_check()