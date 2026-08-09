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
import wave
from pathlib import Path

from ai.tts.models import SpeechRequest
from ai.tts.service import TTSService

from ai.pipeline.contracts import (
    VideoDubbingRequest,
    VideoDubbingResult,
)


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

    def __init__(
        self,
        tts_service: TTSService,
    ) -> None:

        self._tts_service = tts_service

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

        generated_segments: list[
            tuple[Path, float, float]
        ] = []

        try:

            # ----------------------------------------------------------
            # TTS
            # ----------------------------------------------------------

            for index, segment in enumerate(
                validated_segments,
                start=1,
            ):

                segment_path = (
                    segment_directory
                    / f"segment_{index:05d}.wav"
                )

                speech_request = SpeechRequest(
                    text=segment["translated_text"],
                    language=request.language,
                    voice=request.voice,
                    output_path=segment_path,
                )

                self._tts_service.synthesize(
                    speech_request
                )

                if not segment_path.exists():

                    raise RuntimeError(
                        "TTS did not generate audio "
                        f"for segment {segment['id']}."
                    )

                generated_segments.append(
                    (
                        segment_path,
                        segment["start"],
                        segment["end"],
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
                voice=request.voice,
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
        generated_segments: list[
            tuple[Path, float, float]
        ],
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

        first_path = generated_segments[0][0]

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
            end
            for _, _, end in generated_segments
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

        for index, (
            segment_path,
            start,
            end,
        ) in enumerate(
            generated_segments
        ):

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
                    ][1]
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

                adjusted_frames = (
                    self._pad_or_trim_audio(
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

                adjusted_frames = (
                    self._resize_audio(
                        frames=frames,
                        current_frames=current_frames,
                        target_frames=available_frames,
                        channels=channels,
                    )
                )

            # ----------------------------------------------------------
            # TTS shorter than target
            # ----------------------------------------------------------

            else:

                adjusted_frames = (
                    self._pad_or_trim_audio(
                        frames=frames,
                        current_frames=current_frames,
                        target_frames=target_frames,
                        frame_size=frame_size,
                    )
                )

            # ----------------------------------------------------------
            # Place audio on timeline
            # ----------------------------------------------------------

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

            output_frames[
                destination_start:
                destination_end
            ] = adjusted_frames[
                :(
                    destination_end
                    - destination_start
                )
            ]

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

    def _pad_or_trim_audio(
        self,
        frames: bytes,
        current_frames: int,
        target_frames: int,
        frame_size: int,
    ) -> bytes:
        """
        Adjust only by padding or trimming.

        Used when the duration difference is small.
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

            return frames[
                :target_bytes
            ]

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
    ) -> bytes:
        """
        Resize 16-bit PCM audio to the target frame count.

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

        import array

        source = array.array(
            "h"
        )

        source.frombytes(
            frames
        )

        result = array.array(
            "h"
        )

        for target_index in range(
            target_frames
        ):

            source_position = (
                target_index
                * current_frames
                / target_frames
            )

            source_index = min(
                int(source_position),
                current_frames - 1,
            )

            source_offset = (
                source_index
                * channels
            )

            for channel in range(
                channels
            ):

                result.append(
                    source[
                        source_offset
                        + channel
                    ]
                )

        return result.tobytes()

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

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(
        self,
    ) -> bool:

        return self._tts_service.health_check()