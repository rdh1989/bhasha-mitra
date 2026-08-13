"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : dubbing_pipeline.py
Purpose     : AI Dubbing Pipeline

Description:
    Generates timestamp-aligned dubbed audio from translation.json.

Pipeline
--------
translation.json
    ↓
Translated Segments
    ↓
TTS Service
    ↓
Timestamp Alignment
    ↓
Audio Assembly
    ↓
Dubbed Audio

Responsibilities
----------------
• Read translation.json
• Process translated segments
• Invoke provider-independent TTSService
• Preserve original segment timing
• Handle TTS duration differences
• Assemble final dubbed audio

The Backend team is responsible for:
• Video handling
• Audio extraction
• ASR
• Translation

The AI Dubbing Pipeline is responsible only for:
• Reading translated segments
• Text-to-Speech generation
• Timestamp-aware audio assembly

Author:
    Bhasha Mitra AI Team

Version:
    1.3
===============================================================================
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from ai.model_manager.manager import ModelManager
from ai.tts.models import SpeechRequest
from ai.tts.service import TTSService

from ai.pipeline.contracts import (
    VideoDubbingRequest,
    VideoDubbingResult,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _TTSTimelineChunk:
    segment_id: int
    audio_path: Path
    start: float
    end: float
    target_duration: float
    generated_duration: float
    action: str


class DubbingPipeline:
    """
    AI dubbing pipeline.

    Input:
        translation.json

    Each translation segment contains:

        id
        start
        end
        source_text
        translated_text

    The generated TTS audio is placed according to the
    original segment timeline.
    """

    # ------------------------------------------------------------------
    # Timing tolerance
    # ------------------------------------------------------------------

    # Small duration differences are handled by silence padding.
    # Larger differences are handled by controlled PCM resampling.
    #
    # This value avoids unnecessary processing for tiny differences.
    DURATION_TOLERANCE_SECONDS = 0.15
    EDGE_FADE_MILLISECONDS = 12
    MAX_RESAMPLE_RATIO = 1.15
    CHUNK_TARGET_MIN_SECONDS = 4.0
    CHUNK_TARGET_MAX_SECONDS = 8.0
    CHUNK_TARGET_HARD_MAX_SECONDS = 9.0
    # Overflow within this margin is left to assembly-time compression
    # instead of triggering expensive text resegmentation.
    SIGNIFICANT_OVERFLOW_RATIO = 1.15
    # Floor for Piper's length_scale when proactively speeding up
    # verbose segments, to keep speech intelligible.
    MIN_LENGTH_SCALE = 0.7
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?\u0964])\s+")
    CLAUSE_SPLIT_PATTERN = re.compile(r"(?<=[,;:])\s+|\s+-\s+")

    def __init__(
        self,
        tts_service: TTSService,
    ) -> None:

        self._tts_service = tts_service
        self._model_manager = ModelManager()

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(
        self,
        request: VideoDubbingRequest,
    ) -> VideoDubbingResult:
        """
        Generate timestamp-aligned dubbed audio.
        """

        translated_text_path = Path(
            request.translated_text_path
        )

        # --------------------------------------------------------------
        # Validate input
        # --------------------------------------------------------------

        if not translated_text_path.exists():

            raise FileNotFoundError(
                f"Translated text file not found: "
                f"{translated_text_path}"
            )

        if not translated_text_path.is_file():

            raise ValueError(
                f"Translated text path is not a file: "
                f"{translated_text_path}"
            )

        # --------------------------------------------------------------
        # Read translation.json
        # --------------------------------------------------------------

        try:

            translation_data = json.loads(
                translated_text_path.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Invalid translation JSON."
            ) from exc

        segments = translation_data.get(
            "segments"
        )

        if not isinstance(
            segments,
            list,
        ) or not segments:

            raise ValueError(
                "Translation contains no segments."
            )

        # --------------------------------------------------------------
        # Validate segments
        # --------------------------------------------------------------

        validated_segments = (
            self._validate_segments(
                segments
            )
        )

        # ------------------------------------------------------------------
        # Voice selection
        # ------------------------------------------------------------------
        # Keep the request contract unchanged, but ignore request.voice for
        # synthesis. The configured Piper voice loaded by ModelManager must
        # be used consistently for every segment.
        configured_voice = self._get_configured_tts_voice()

        # --------------------------------------------------------------
        # Output
        # --------------------------------------------------------------

        output_path = Path(
            request.output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------------------
        # Temporary directory
        # --------------------------------------------------------------

        segment_directory = (
            output_path.parent
            / f".{output_path.stem}_segments"
        )

        segment_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        generated_segments: list[_TTSTimelineChunk] = []

        try:

            # ----------------------------------------------------------
            # TTS
            # ----------------------------------------------------------

            for index, segment in enumerate(
                validated_segments,
                start=1,
            ):
                generated_segments.extend(
                    self._synthesize_segment_chunks(
                        segment=segment,
                        request=request,
                        configured_voice=configured_voice,
                        segment_directory=segment_directory,
                        segment_index=index,
                    )
                )

            # ----------------------------------------------------------
            # Assemble final audio
            # ----------------------------------------------------------

            self._assemble_audio(
                generated_segments=generated_segments,
                output_path=output_path,
            )

            # ----------------------------------------------------------
            # Final metadata
            # ----------------------------------------------------------

            sample_rate, duration = (
                self._read_wav_metadata(
                    output_path
                )
            )

            return VideoDubbingResult(
                audio_file=output_path,
                language=request.language,
                voice=configured_voice,
                sample_rate=sample_rate,
                duration=duration,
            )

        finally:

            self._cleanup_segments(
                segment_directory
            )

    # ------------------------------------------------------------------
    # Validate Translation Segments
    # ------------------------------------------------------------------

    def _validate_segments(
        self,
        segments: list[dict],
    ) -> list[dict]:
        """
        Validate and normalize translation segments.
        """

        validated: list[dict] = []

        previous_end = 0.0

        for segment in segments:

            if not isinstance(
                segment,
                dict,
            ):

                raise ValueError(
                    "Invalid translation segment."
                )

            try:

                segment_id = int(
                    segment["id"]
                )

                start = float(
                    segment["start"]
                )

                end = float(
                    segment["end"]
                )

                translated_text = str(
                    segment["translated_text"]
                ).strip()

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:

                raise ValueError(
                    "Invalid translation segment data."
                ) from exc

            if start < 0:

                raise ValueError(
                    f"Segment {segment_id} has "
                    "negative start time."
                )

            if end <= start:

                raise ValueError(
                    f"Segment {segment_id} has "
                    "invalid timing."
                )

            if not translated_text:

                raise ValueError(
                    f"Segment {segment_id} has "
                    "empty translated text."
                )

            # ----------------------------------------------------------
            # Timeline validation
            # ----------------------------------------------------------

            if start < previous_end:

                raise ValueError(
                    "Translation segments contain "
                    f"overlapping timestamps around "
                    f"segment {segment_id}."
                )

            validated.append(
                {
                    "id": segment_id,
                    "start": start,
                    "end": end,
                    "translated_text": translated_text,
                }
            )

            previous_end = end

        return validated

    # ------------------------------------------------------------------
    # Audio Assembly
    # ------------------------------------------------------------------

    def _assemble_audio(
        self,
        generated_segments: list[_TTSTimelineChunk],
        output_path: Path,
    ) -> None:
        """
        Assemble generated TTS segments on the original timeline.

        Each segment is placed at its original start time.

        Duration handling:
            • Slightly shorter audio -> silence padding.
            • Slightly longer audio -> controlled adjustment.
            • Large duration differences -> controlled adjustment
              to prevent overlap with the next segment.
        """

        if not generated_segments:

            raise ValueError(
                "No generated audio segments available."
            )

        # --------------------------------------------------------------
        # Read first WAV parameters
        # --------------------------------------------------------------

        first_path = generated_segments[0].audio_path

        with wave.open(
            str(first_path),
            "rb",
        ) as first:

            channels = first.getnchannels()
            sample_width = first.getsampwidth()
            sample_rate = first.getframerate()

        if sample_width != 2:

            raise ValueError(
                "Dubbing currently supports "
                "16-bit PCM WAV audio only."
            )

        # --------------------------------------------------------------
        # Determine final timeline
        # --------------------------------------------------------------

        final_end = max(
            chunk.end
            for chunk in generated_segments
        )

        total_frames = int(
            final_end * sample_rate
        )

        frame_size = (
            channels * sample_width
        )

        output_frames = bytearray(
            total_frames * frame_size
        )

        # --------------------------------------------------------------
        # Process each segment
        # --------------------------------------------------------------

        for index, chunk in enumerate(generated_segments):

            segment_path = chunk.audio_path
            start = chunk.start
            end = chunk.end

            target_duration = (
                end - start
            )

            target_frames = int(
                target_duration
                * sample_rate
            )

            # ----------------------------------------------------------
            # Read TTS audio
            # ----------------------------------------------------------

            with wave.open(
                str(segment_path),
                "rb",
            ) as wav_file:

                if (
                    wav_file.getnchannels()
                    != channels
                    or
                    wav_file.getsampwidth()
                    != sample_width
                    or
                    wav_file.getframerate()
                    != sample_rate
                ):

                    raise ValueError(
                        "TTS audio parameters differ "
                        f"for segment: {segment_path}"
                    )

                frames = wav_file.readframes(
                    wav_file.getnframes()
                )

            current_frames = (
                len(frames)
                // frame_size
            )

            current_duration = (
                current_frames
                / sample_rate
            )

            duration_ratio = (
                current_duration / target_duration
                if target_duration > 0
                else 1.0
            )

            logger.info(
                "DUBBING TIMING | segment_id=%s | target_duration=%.3f | generated_duration=%.3f | duration_ratio=%.3f | action=%s",
                chunk.segment_id,
                chunk.target_duration,
                chunk.generated_duration,
                duration_ratio,
                chunk.action,
            )

            duration_difference = (
                current_duration
                - target_duration
            )

            # ----------------------------------------------------------
            # Determine available timeline
            # ----------------------------------------------------------

            available_duration = (
                target_duration
            )

            if index + 1 < len(
                generated_segments
            ):

                next_start = (
                    generated_segments[
                        index + 1
                    ].start
                )

                available_duration = max(
                    0.0,
                    next_start - start,
                )

            available_frames = int(
                available_duration
                * sample_rate
            )

            # ----------------------------------------------------------
            # Small difference
            # ----------------------------------------------------------

            if abs(
                duration_difference
            ) <= self.DURATION_TOLERANCE_SECONDS:

                if current_frames > target_frames:
                    adjusted_frames = self._resize_audio(
                        frames=frames,
                        current_frames=current_frames,
                        target_frames=target_frames,
                        channels=channels,
                        sample_rate=sample_rate,
                        segment_id=chunk.segment_id,
                    )
                else:
                    adjusted_frames = (
                        self._pad_audio(
                            frames=frames,
                            current_frames=current_frames,
                            target_frames=target_frames,
                            frame_size=frame_size,
                        )
                    )

            # ----------------------------------------------------------
            # TTS longer than target
            # ----------------------------------------------------------

            elif current_duration > available_duration:
                if available_frames <= 0:
                    adjusted_frames = b""
                else:
                    resample_ratio = (
                        current_frames / available_frames
                    )
                    adjusted_frames = self._resize_audio(
                        frames=frames,
                        current_frames=current_frames,
                        target_frames=available_frames,
                        channels=channels,
                        sample_rate=sample_rate,
                        segment_id=chunk.segment_id,
                    )

            # ----------------------------------------------------------
            # TTS shorter than target
            # ----------------------------------------------------------

            else:

                adjusted_frames = (
                    self._pad_audio(
                        frames=frames,
                        current_frames=current_frames,
                        target_frames=target_frames,
                        frame_size=frame_size,
                    )
                )

            # ----------------------------------------------------------
            # Place audio on timeline
            # ----------------------------------------------------------

            adjusted_frames = self._apply_edge_fade(
                frames=adjusted_frames,
                channels=channels,
                sample_rate=sample_rate,
            )

            start_frame = int(
                start * sample_rate
            )

            destination_start = (
                start_frame * frame_size
            )

            destination_end = min(
                destination_start
                + len(adjusted_frames),
                len(output_frames),
            )

            if destination_start >= len(
                output_frames
            ):

                continue

            source_slice = adjusted_frames[
                :(
                    destination_end
                    - destination_start
                )
            ]

            destination_slice = bytes(
                output_frames[
                    destination_start:
                    destination_end
                ]
            )

            mixed_slice = self._mix_pcm16(
                destination_slice=destination_slice,
                source_slice=source_slice,
            )

            output_frames[
                destination_start:
                destination_end
            ] = mixed_slice

        # --------------------------------------------------------------
        # Write final WAV
        # --------------------------------------------------------------

        with wave.open(
            str(output_path),
            "wb",
        ) as output:

            output.setnchannels(
                channels
            )

            output.setsampwidth(
                sample_width
            )

            output.setframerate(
                sample_rate
            )

            output.writeframes(
                bytes(output_frames)
            )

    # ------------------------------------------------------------------
    # Pad / Trim
    # ------------------------------------------------------------------

    def _pad_audio(
        self,
        frames: bytes,
        current_frames: int,
        target_frames: int,
        frame_size: int,
    ) -> bytes:
        """
        Adjust only by padding.

        Shorter-than-target audio keeps natural speed and the remaining
        timeline is left as silence.
        """

        if target_frames <= 0:

            return b""

        target_bytes = (
            target_frames * frame_size
        )

        current_bytes = (
            current_frames * frame_size
        )

        if current_bytes >= target_bytes:

            return frames

        return (
            frames
            + (
                b"\x00"
                * (
                    target_bytes
                    - current_bytes
                )
            )
        )

    # ------------------------------------------------------------------
    # Audio Resize
    # ------------------------------------------------------------------

    def _resize_audio(
        self,
        frames: bytes,
        current_frames: int,
        target_frames: int,
        channels: int,
        sample_rate: int,
        segment_id: int | None = None,
    ) -> bytes:
        """
        Pitch-preserving time stretch to the target frame count.

        This is used only when TTS exceeds the available timeline.

        It preserves the timeline and prevents overlap with
        subsequent segments.
        """

        if target_frames <= 0:

            return b""

        if current_frames <= 0:

            return b"\x00" * (
                target_frames
                * channels
                * 2
            )

        if current_frames == target_frames:

            return frames

        stretch_ratio = (
            current_frames / target_frames
        )

        # Beyond this cap, prefer natural speech (and mild timeline drift)
        # over unintelligible speed-up.
        applied_ratio = min(
            stretch_ratio,
            self.MAX_RESAMPLE_RATIO,
        )

        with tempfile.TemporaryDirectory() as temp_directory:

            temp_directory_path = Path(
                temp_directory
            )
            input_path = temp_directory_path / "input.wav"
            output_path = temp_directory_path / "output.wav"

            with wave.open(
                str(input_path),
                "wb",
            ) as wav_file:

                wav_file.setnchannels(
                    channels
                )
                wav_file.setsampwidth(
                    2
                )
                wav_file.setframerate(
                    sample_rate
                )
                wav_file.writeframes(
                    frames
                )

            ffmpeg_executable = (
                self._resolve_ffmpeg_executable()
            )

            if ffmpeg_executable is None:
                raise RuntimeError(
                    "FFmpeg is required for pitch-preserving TTS time stretching."
                )

            if segment_id is not None:
                logger.info(
                    "DUBBING TIMING | segment_id=%s | generated_duration=%.3f | target_duration=%.3f | stretch_ratio=%.3f | applied_ratio=%.3f | action=%s",
                    segment_id,
                    current_frames / sample_rate,
                    target_frames / sample_rate,
                    stretch_ratio,
                    applied_ratio,
                    "time_stretch",
                )

            command = [
                str(ffmpeg_executable),
                "-y",
                "-i",
                str(input_path),
                "-filter:a",
                self._build_atempo_filter(applied_ratio),
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]

            try:
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    "Pitch-preserving TTS time stretching failed."
                ) from exc

            with wave.open(
                str(output_path),
                "rb",
            ) as wav_file:

                return wav_file.readframes(
                    wav_file.getnframes()
                )

    def _apply_edge_fade(
        self,
        frames: bytes,
        channels: int,
        sample_rate: int,
    ) -> bytes:
        """
        Apply short fades at segment boundaries to reduce click artifacts.
        """

        if not frames:
            return frames

        import array

        samples = array.array(
            "h"
        )
        samples.frombytes(
            frames
        )

        frame_count = len(samples) // channels

        fade_frames = min(
            int(sample_rate * self.EDGE_FADE_MILLISECONDS / 1000),
            frame_count // 2,
        )

        if fade_frames <= 0:
            return frames

        for frame_index in range(fade_frames):

            gain = (frame_index + 1) / fade_frames

            head_offset = frame_index * channels
            tail_offset = (frame_count - 1 - frame_index) * channels

            for channel in range(channels):

                head_index = head_offset + channel
                tail_index = tail_offset + channel

                samples[head_index] = int(
                    samples[head_index] * gain
                )
                samples[tail_index] = int(
                    samples[tail_index] * gain
                )

        return samples.tobytes()

    @staticmethod
    def _build_atempo_filter(stretch_ratio: float) -> str:
        """
        Build an ffmpeg atempo filter chain for the requested ratio.
        """

        remaining = stretch_ratio
        filters: list[str] = []

        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0

        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5

        filters.append(f"atempo={remaining:.6f}")

        return ",".join(filters)

    @staticmethod
    def _resolve_ffmpeg_executable() -> Path | None:
        """
        Resolve the bundled or PATH ffmpeg executable.
        """

        project_root = Path(__file__).resolve().parents[3]
        bundled_ffmpeg = (
            project_root
            / "models"
            / "third_party"
            / "ffmpeg"
            / "ffmpeg-8.1.2"
            / "bin"
            / "ffmpeg.exe"
        )

        if bundled_ffmpeg.is_file():
            return bundled_ffmpeg

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return Path(system_ffmpeg)

        return None

    def _synthesize_segment_chunks(
        self,
        segment: dict,
        request: VideoDubbingRequest,
        configured_voice: str,
        segment_directory: Path,
        segment_index: int,
    ) -> list[_TTSTimelineChunk]:
        """
        Generate one or more natural TTS chunks for a segment.
        """

        segment_id = int(segment["id"])
        segment_start = float(segment["start"])
        segment_end = float(segment["end"])
        segment_text = str(segment["translated_text"]).strip()
        segment_duration = max(segment_end - segment_start, 0.001)

        text_chunks = self._split_text_for_tts(
            text=segment_text,
            segment_duration=segment_duration,
        )

        windows = self._allocate_chunk_windows(
            start=segment_start,
            end=segment_end,
            texts=text_chunks,
        )

        generated: list[_TTSTimelineChunk] = []

        for chunk_index, (chunk_text, chunk_start, chunk_end) in enumerate(
            windows,
            start=1,
        ):
            generated.extend(
                self._synthesize_window_with_regeneration(
                    segment_id=segment_id,
                    text=chunk_text,
                    start=chunk_start,
                    end=chunk_end,
                    request=request,
                    configured_voice=configured_voice,
                    segment_directory=segment_directory,
                    file_stem=f"segment_{segment_index:05d}_{chunk_index:02d}",
                    depth=0,
                )
            )

        return generated

    def _synthesize_window_with_regeneration(
        self,
        segment_id: int,
        text: str,
        start: float,
        end: float,
        request: VideoDubbingRequest,
        configured_voice: str,
        segment_directory: Path,
        file_stem: str,
        depth: int,
        length_scale: float | None = None,
    ) -> list[_TTSTimelineChunk]:
        """
        Synthesize a chunk and regenerate with finer segmentation when needed.
        """

        target_duration = max(end - start, 0.001)
        chunk_path = segment_directory / f"{file_stem}_d{depth}.wav"

        speech_request = SpeechRequest(
            text=text,
            language=request.language,
            voice=configured_voice,
            output_path=chunk_path,
            length_scale=length_scale,
        )

        self._tts_service.synthesize(
            speech_request
        )

        if not chunk_path.exists():
            raise RuntimeError(
                "TTS did not generate audio "
                f"for segment {segment_id}."
            )

        _, generated_duration = self._read_wav_metadata(chunk_path)

        if generated_duration is None:
            generated_duration = 0.0

        ratio = (
            generated_duration / target_duration
            if target_duration > 0
            else 1.0
        )

        if ratio > self.SIGNIFICANT_OVERFLOW_RATIO and depth < 4:

            # Proactively ask Piper to speak faster before falling back to
            # the more expensive text resegmentation path.
            if length_scale is None:
                proactive_scale = max(
                    self.MIN_LENGTH_SCALE,
                    min(1.0, 1.0 / ratio),
                )
                if proactive_scale < 1.0:
                    logger.info(
                        "DUBBING TIMING | segment_id=%s | target_duration=%.3f | generated_duration=%.3f | duration_ratio=%.3f | action=%s",
                        segment_id,
                        target_duration,
                        generated_duration,
                        ratio,
                        "proactive_speed_regenerate",
                    )
                    return self._synthesize_window_with_regeneration(
                        segment_id=segment_id,
                        text=text,
                        start=start,
                        end=end,
                        request=request,
                        configured_voice=configured_voice,
                        segment_directory=segment_directory,
                        file_stem=file_stem,
                        depth=depth + 1,
                        length_scale=proactive_scale,
                    )

            subparts = self._split_text_into_subparts(text)
            if len(subparts) > 1:
                action = "resegment_regenerate"
                logger.info(
                    "DUBBING TIMING | segment_id=%s | target_duration=%.3f | generated_duration=%.3f | duration_ratio=%.3f | action=%s",
                    segment_id,
                    target_duration,
                    generated_duration,
                    ratio,
                    action,
                )
                windows = self._allocate_chunk_windows(
                    start=start,
                    end=end,
                    texts=subparts,
                )
                regenerated: list[_TTSTimelineChunk] = []
                for index, (subtext, substart, subend) in enumerate(
                    windows,
                    start=1,
                ):
                    regenerated.extend(
                        self._synthesize_window_with_regeneration(
                            segment_id=segment_id,
                            text=subtext,
                            start=substart,
                            end=subend,
                            request=request,
                            configured_voice=configured_voice,
                            segment_directory=segment_directory,
                            file_stem=f"{file_stem}_r{index:02d}",
                            depth=depth + 1,
                            length_scale=length_scale,
                        )
                    )
                return regenerated

        action = "keep_natural"
        if ratio > 1.0:
            action = "mild_compress" if ratio <= self.MAX_RESAMPLE_RATIO else "compress_after_regen"
        elif ratio < 1.0:
            action = "pad_silence"

        return [
            _TTSTimelineChunk(
                segment_id=segment_id,
                audio_path=chunk_path,
                start=start,
                end=end,
                target_duration=target_duration,
                generated_duration=generated_duration,
                action=action,
            )
        ]

    def _split_text_for_tts(
        self,
        text: str,
        segment_duration: float,
    ) -> list[str]:
        """
        Split text at sentence/clause boundaries for natural TTS chunks.
        """

        units: list[str] = []
        for sentence in self.SENTENCE_SPLIT_PATTERN.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            clauses = [
                clause.strip()
                for clause in self.CLAUSE_SPLIT_PATTERN.split(sentence)
                if clause.strip()
            ]
            if clauses:
                units.extend(clauses)

        if not units:
            units = [text.strip()]

        if segment_duration <= self.CHUNK_TARGET_MAX_SECONDS:
            return [" ".join(units).strip()]

        desired_chunks = max(
            1,
            int(round(segment_duration / 6.0)),
        )

        packed: list[str] = []
        current_parts: list[str] = []
        current_weight = 0
        total_weight = sum(max(len(part), 1) for part in units)
        target_weight = max(1, total_weight // desired_chunks)

        for part in units:
            part_weight = max(len(part), 1)
            if current_parts and current_weight + part_weight > target_weight:
                packed.append(" ".join(current_parts).strip())
                current_parts = []
                current_weight = 0
            current_parts.append(part)
            current_weight += part_weight

        if current_parts:
            packed.append(" ".join(current_parts).strip())

        return [chunk for chunk in packed if chunk]

    def _split_text_into_subparts(self, text: str) -> list[str]:
        """
        Split text into smaller natural parts for regeneration.
        """

        clauses = [
            clause.strip()
            for clause in self.CLAUSE_SPLIT_PATTERN.split(text)
            if clause.strip()
        ]

        if len(clauses) > 1:
            return clauses

        words = text.split()
        if len(words) <= 2:
            return [text.strip()]

        midpoint = len(words) // 2
        return [
            " ".join(words[:midpoint]).strip(),
            " ".join(words[midpoint:]).strip(),
        ]

    def _allocate_chunk_windows(
        self,
        start: float,
        end: float,
        texts: list[str],
    ) -> list[tuple[str, float, float]]:
        """
        Allocate contiguous timeline windows proportionally to text length.
        """

        duration = max(end - start, 0.001)
        if not texts:
            return []

        weights = [max(len(text.strip()), 1) for text in texts]
        weight_sum = sum(weights)

        windows: list[tuple[str, float, float]] = []
        cursor = start

        for index, text in enumerate(texts):
            if index == len(texts) - 1:
                window_end = end
            else:
                portion = duration * (weights[index] / weight_sum)
                window_end = min(end, cursor + portion)
            windows.append((text, cursor, window_end))
            cursor = window_end

        return self._rebalance_oversized_windows(windows)

    def _rebalance_oversized_windows(
        self,
        windows: list[tuple[str, float, float]],
        depth: int = 0,
    ) -> list[tuple[str, float, float]]:
        """
        Split windows that exceed the preferred hard max duration.
        """

        if depth >= 3:
            return windows

        balanced: list[tuple[str, float, float]] = []

        for text, start, end in windows:
            duration = end - start

            if duration <= self.CHUNK_TARGET_HARD_MAX_SECONDS:
                balanced.append((text, start, end))
                continue

            subparts = self._split_text_into_subparts(text)

            if len(subparts) <= 1:
                balanced.append((text, start, end))
                continue

            split_windows = self._allocate_chunk_windows(
                start=start,
                end=end,
                texts=subparts,
            )

            balanced.extend(
                self._rebalance_oversized_windows(
                    split_windows,
                    depth=depth + 1,
                )
            )

        return balanced

    def _mix_pcm16(
        self,
        destination_slice: bytes,
        source_slice: bytes,
    ) -> bytes:
        """
        Mix two 16-bit PCM buffers with saturation to avoid overflow.
        """

        import array

        destination = array.array(
            "h"
        )
        destination.frombytes(
            destination_slice
        )

        source = array.array(
            "h"
        )
        source.frombytes(
            source_slice
        )

        count = min(
            len(destination),
            len(source),
        )

        for index in range(count):

            mixed = destination[index] + source[index]

            if mixed > 32767:
                mixed = 32767
            elif mixed < -32768:
                mixed = -32768

            destination[index] = mixed

        return destination.tobytes()

    # ------------------------------------------------------------------
    # WAV Metadata
    # ------------------------------------------------------------------

    def _read_wav_metadata(
        self,
        audio_path: Path,
    ) -> tuple[int, float | None]:

        with wave.open(
            str(audio_path),
            "rb",
        ) as wav_file:

            sample_rate = (
                wav_file.getframerate()
            )

            frame_count = (
                wav_file.getnframes()
            )

        duration = (
            frame_count / sample_rate
            if sample_rate
            else None
        )

        return sample_rate, duration

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_segments(
        self,
        segment_directory: Path,
    ) -> None:

        if not segment_directory.exists():
            return

        for file_path in (
            segment_directory.iterdir()
        ):

            try:

                if file_path.is_file():
                    file_path.unlink()

            except OSError:
                pass

        try:

            segment_directory.rmdir()

        except OSError:
            pass

    def _get_configured_tts_voice(self) -> str:
        """
        Return the configured default TTS voice from ModelManager metadata.
        """

        metadata = self._model_manager.get_default_metadata(
            "tts"
        )

        voice = str(
            metadata.get("model", "")
        ).strip()

        if not voice:
            raise ValueError(
                "Configured TTS voice is missing in model metadata."
            )

        return voice

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(
        self,
    ) -> bool:

        return self._tts_service.health_check()