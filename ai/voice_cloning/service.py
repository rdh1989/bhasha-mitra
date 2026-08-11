"""
===============================================================================
Bhasha Mitra - Voice Preserving Dubbing
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Voice-preserving dubbing orchestration
===============================================================================
"""

from __future__ import annotations

import json
import logging
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

from .providers.indicf5_provider import IndicF5Engine
from .models import (
    VoiceDubbingRequest,
    VoiceDubbingResult,
)
from .reference_extractor import (
    ReferenceExtractor,
)


logger = logging.getLogger(__name__)


class VoiceDubbingService:
    """
    Voice-preserving dubbing service.

    Input:
        audio.wav
        translation.json

    Output:
        dubbed_audio.wav
    """

    SAMPLE_RATE = 24000

    def __init__(
        self,
        model_path: str | Path,
    ) -> None:

        self._reference_extractor = (
            ReferenceExtractor(
                target_sample_rate=self.SAMPLE_RATE,
                minimum_duration=4.0,
                maximum_duration=10.0,
            )
        )

        self._engine = IndicF5Engine(
            model_path=model_path
        )

    # ------------------------------------------------------------------

    def dub(
        self,
        request: VoiceDubbingRequest,
    ) -> VoiceDubbingResult:

        if request.language.lower() != "mr":

            raise ValueError(
                "Current IndicF5 voice-dubbing "
                "implementation is configured for Marathi."
            )

        if not request.audio_path.is_file():

            raise FileNotFoundError(
                f"Audio file does not exist: "
                f"{request.audio_path}"
            )

        if not request.translation_path.is_file():

            raise FileNotFoundError(
                f"Translation file does not exist: "
                f"{request.translation_path}"
            )

        if request.transcript_path is not None and not request.transcript_path.is_file():
            raise FileNotFoundError(
                f"Transcript file does not exist: "
                f"{request.transcript_path}"
            )

        output_path = request.output_path
        if output_path is None:
            output_path = request.translation_path.with_suffix(".wav")
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------------------
        # Step 1 - Load translation/transcript segments
        # --------------------------------------------------------------

        segments = self._merge_segments(
            transcript_path=request.transcript_path,
            translation_path=request.translation_path,
        )

        if not segments:
            raise RuntimeError(
                "No translation segments found."
            )

        # --------------------------------------------------------------
        # Step 2 - Create speaker reference
        # --------------------------------------------------------------

        reference_path = (
            output_path.parent
            / "_voice_reference.wav"
        )

        reference = (
            self._reference_extractor.extract_from_segments(
                audio_path=request.audio_path,
                segments=segments,
                output_path=reference_path,
            )
        )

        logger.info(
            "VOICE DUBBING REFERENCE READY | "
            "audio=%s | text=%s",
            reference.path,
            reference.text,
        )

        # --------------------------------------------------------------
        # Step 3 - Generate individual segments
        # --------------------------------------------------------------

        generated_segments: list[
            tuple[float, float, Path]
        ] = []

        segment_directory = (
            output_path.parent
            / "_voice_segments"
        )

        segment_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for index, segment in enumerate(
            segments,
            start=1,
        ):

            translated_text = str(
                segment.get(
                    "translated_text",
                    "",
                )
            ).strip()

            if not translated_text:
                logger.warning(
                    "SKIPPING EMPTY TRANSLATION | "
                    "index=%s",
                    index,
                )
                continue

            start = float(
                segment["start"]
            )

            end = float(
                segment["end"]
            )

            segment_output = (
                segment_directory
                / f"segment_{index:04d}.wav"
            )

            logger.info(
                "VOICE DUB SEGMENT | "
                "index=%s | "
                "start=%.2f | "
                "end=%.2f | "
                "text_length=%s",
                index,
                start,
                end,
                len(translated_text),
            )

            self._engine.synthesize(
                text=translated_text,
                reference_audio=reference.path,
                reference_text=reference.text,
                output_path=segment_output,
            )

            generated_segments.append(
                (
                    start,
                    end,
                    segment_output,
                )
            )

        if not generated_segments:

            raise RuntimeError(
                "No audio segments were generated."
            )

        # --------------------------------------------------------------
        # Step 4 - Assemble final audio
        # --------------------------------------------------------------

        self._assemble_audio(
            generated_segments,
            output_path,
        )

        duration = self._get_duration(
            output_path
        )

        logger.info(
            "VOICE DUBBING COMPLETED | "
            "output=%s | "
            "segments=%s | "
            "duration=%.2fs",
            request.output_path,
            len(generated_segments),
            duration or 0.0,
        )

        return VoiceDubbingResult(
            audio_path=output_path,
            language=request.language,
            sample_rate=self.SAMPLE_RATE,
            duration=duration,
            segments_generated=len(
                generated_segments
            ),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _load_json_segments(
        path: Path,
    ) -> list[dict]:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        segments = data.get("segments", [])

        if not isinstance(segments, list):
            raise ValueError(
                f"{path.name} does not contain a valid segments list."
            )

        return segments

    @classmethod
    def _merge_segments(
        cls,
        transcript_path: Path | None,
        translation_path: Path,
    ) -> list[dict]:

        translation_segments = cls._load_json_segments(
            translation_path
        )

        if transcript_path is None:
            return [
                {
                    "id": segment.get("id", index),
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "source_text": str(
                        segment.get("source_text")
                        or segment.get("text")
                        or ""
                    ).strip(),
                    "translated_text": str(
                        segment.get("translated_text", "")
                    ).strip(),
                }
                for index, segment in enumerate(translation_segments)
            ]

        transcript_segments = cls._load_json_segments(
            transcript_path
        )

        transcript_lookup = {
            str(segment.get("id")): segment
            for segment in transcript_segments
            if segment.get("id") is not None
        }

        merged_segments: list[dict] = []

        for index, segment in enumerate(translation_segments):
            segment_id = segment.get("id")
            transcript_segment = transcript_lookup.get(str(segment_id))

            source_text = ""
            if transcript_segment is not None:
                source_text = str(
                    transcript_segment.get("text", "")
                ).strip()
            else:
                source_text = str(
                    segment.get("source_text", "")
                ).strip()

            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            if transcript_segment is not None:
                start = transcript_segment.get("start", start)
                end = transcript_segment.get("end", end)

            merged_segments.append(
                {
                    "id": segment_id if segment_id is not None else index,
                    "start": float(start),
                    "end": float(end),
                    "source_text": source_text,
                    "translated_text": str(
                        segment.get("translated_text", "")
                    ).strip(),
                }
            )

        return merged_segments

    # ------------------------------------------------------------------

    def _assemble_audio(
        self,
        segments: list[
            tuple[float, float, Path]
        ],
        output_path: Path,
    ) -> None:

        # Determine final timeline length.
        final_end = max(
            end
            for _, end, _ in segments
        )

        total_samples = int(
            final_end
            * self.SAMPLE_RATE
        )

        final_audio = np.zeros(
            total_samples,
            dtype=np.float32,
        )

        for start, end, segment_path in segments:

            audio, sample_rate = sf.read(
                str(segment_path),
                dtype="float32",
            )

            if sample_rate != self.SAMPLE_RATE:

                raise RuntimeError(
                    "Generated IndicF5 audio "
                    "has unexpected sample rate."
                )

            if audio.ndim == 2:

                audio = np.mean(
                    audio,
                    axis=1,
                )

            start_sample = int(
                start
                * self.SAMPLE_RATE
            )

            available = (
                len(final_audio)
                - start_sample
            )

            if available <= 0:
                continue

            audio = audio[:available]

            end_sample = (
                start_sample
                + len(audio)
            )

            final_audio[
                start_sample:end_sample
            ] = audio

        # Final conservative normalization.
        peak = float(
            np.max(
                np.abs(final_audio)
            )
        )

        if peak > 0.95:

            final_audio *= (
                0.95 / peak
            )

        sf.write(
            str(output_path),
            np.clip(
                final_audio,
                -1.0,
                1.0,
            ),
            self.SAMPLE_RATE,
            subtype="PCM_16",
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _get_duration(
        path: Path,
    ) -> float | None:

        try:

            with wave.open(
                str(path),
                "rb",
            ) as wav:

                sample_rate = (
                    wav.getframerate()
                )

                frames = (
                    wav.getnframes()
                )

            if sample_rate <= 0:
                return None

            return frames / sample_rate

        except Exception:

            return None