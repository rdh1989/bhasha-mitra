"""
===============================================================================
Bhasha Mitra - Voice Preserving Dubbing
-------------------------------------------------------------------------------
Module      : reference_extractor.py
Purpose     : Extract a high-quality speaker reference from original audio
===============================================================================
"""

from __future__ import annotations

import json
import logging
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


logger = logging.getLogger(__name__)


TARGET_SAMPLE_RATE = 24000


@dataclass(slots=True)
class ReferenceAudio:
    path: Path
    text: str
    start: float
    end: float


class ReferenceExtractor:
    """
    Extracts a clean speaker-reference segment.

    IndicF5 requires:
        1. Reference audio
        2. Text spoken in that reference audio

    The source_text in translation.json provides the reference transcript.
    """

    def __init__(
        self,
        target_sample_rate: int = TARGET_SAMPLE_RATE,
        minimum_duration: float = 4.0,
        maximum_duration: float = 10.0,
    ) -> None:

        self._sample_rate = target_sample_rate
        self._minimum_duration = minimum_duration
        self._maximum_duration = maximum_duration

    def extract(
        self,
        audio_path: Path,
        translation_path: Path,
        output_path: Path,
    ) -> ReferenceAudio:

        if not audio_path.is_file():
            raise FileNotFoundError(
                f"Audio file does not exist: {audio_path}"
            )

        if not translation_path.is_file():
            raise FileNotFoundError(
                f"Translation file does not exist: {translation_path}"
            )

        segments = self._load_segments(
            translation_path
        )

        return self.extract_from_segments(
            audio_path=audio_path,
            segments=segments,
            output_path=output_path,
        )

    def extract_from_segments(
        self,
        audio_path: Path,
        segments: list[dict],
        output_path: Path,
    ) -> ReferenceAudio:

        if not audio_path.is_file():
            raise FileNotFoundError(
                f"Audio file does not exist: {audio_path}"
            )

        if not segments:
            raise RuntimeError(
                "No segments available for voice reference extraction."
            )

        selected = self._select_reference_segment(
            segments
        )

        start = float(selected["start"])
        end = float(selected["end"])

        source_text = self._segment_text(
            selected
        )

        if not source_text:
            raise RuntimeError(
                "Selected reference segment has no usable reference text."
            )

        duration = end - start

        logger.info(
            "VOICE REFERENCE SELECTED | "
            "start=%.2fs | end=%.2fs | duration=%.2fs",
            start,
            end,
            duration,
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        audio, sample_rate = sf.read(
            str(audio_path),
            dtype="float32",
        )

        # Convert stereo → mono.
        if audio.ndim == 2:
            audio = np.mean(
                audio,
                axis=1,
            )

        # Resample to IndicF5's expected output/reference rate.
        if sample_rate != self._sample_rate:

            audio = self._resample(
                audio,
                sample_rate,
                self._sample_rate,
            )

            sample_rate = self._sample_rate

        start_frame = max(
            0,
            int(start * sample_rate),
        )

        end_frame = min(
            len(audio),
            int(end * sample_rate),
        )

        reference = audio[
            start_frame:end_frame
        ]

        if len(reference) == 0:
            raise RuntimeError(
                "Reference audio extraction produced empty audio."
            )

        sf.write(
            str(output_path),
            reference,
            self._sample_rate,
            subtype="PCM_16",
        )

        logger.info(
            "VOICE REFERENCE CREATED | "
            "path=%s | duration=%.2fs | sample_rate=%s",
            output_path,
            len(reference) / self._sample_rate,
            self._sample_rate,
        )

        return ReferenceAudio(
            path=output_path,
            text=source_text,
            start=start,
            end=end,
        )

    # ------------------------------------------------------------------

    def _load_segments(
        self,
        translation_path: Path,
    ) -> list[dict]:

        with translation_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        segments = data.get("segments")

        if not isinstance(
            segments,
            list,
        ):
            raise ValueError(
                "translation.json does not contain a valid segments list."
            )

        return segments

    # ------------------------------------------------------------------

    def _select_reference_segment(
        self,
        segments: list[dict],
    ) -> dict:

        candidates = []

        for segment in segments:

            try:
                start = float(
                    segment["start"]
                )

                end = float(
                    segment["end"]
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            text = self._segment_text(
                segment
            )

            duration = end - start

            if not text:
                continue

            if duration < self._minimum_duration:
                continue

            if duration <= self._maximum_duration:

                candidates.append(
                    (
                        duration,
                        segment,
                    )
                )

        if not candidates:

            # Fallback to the longest valid segment.
            fallback = []

            for segment in segments:

                try:
                    duration = (
                        float(segment["end"])
                        - float(segment["start"])
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                if self._segment_text(segment):
                    fallback.append(
                        (
                            duration,
                            segment,
                        )
                    )

            if not fallback:
                raise RuntimeError(
                    "Unable to find a usable voice reference segment."
                )

            fallback.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            return fallback[0][1]

        # Prefer a reference close to 7–8 seconds.
        candidates.sort(
            key=lambda item: abs(
                item[0] - 8.0
            )
        )

        return candidates[0][1]

    @staticmethod
    def _segment_text(
        segment: dict,
    ) -> str:

        for key in (
            "source_text",
            "text",
            "translated_text",
        ):

            value = str(
                segment.get(key, "")
            ).strip()

            if value:
                return value

        return ""

    # ------------------------------------------------------------------

    @staticmethod
    def _resample(
        audio: np.ndarray,
        source_rate: int,
        target_rate: int,
    ) -> np.ndarray:

        if source_rate == target_rate:
            return audio

        duration = len(audio) / source_rate

        target_length = int(
            duration * target_rate
        )

        old_positions = np.linspace(
            0.0,
            1.0,
            len(audio),
        )

        new_positions = np.linspace(
            0.0,
            1.0,
            target_length,
        )

        return np.interp(
            new_positions,
            old_positions,
            audio,
        ).astype(np.float32)