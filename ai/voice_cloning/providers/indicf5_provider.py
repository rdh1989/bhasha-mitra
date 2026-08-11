"""
===============================================================================
Bhasha Mitra - Voice Preserving Dubbing
-------------------------------------------------------------------------------
Module      : indicf5_engine.py
Purpose     : IndicF5 inference engine
===============================================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import soundfile as sf
from transformers import AutoModel


logger = logging.getLogger(__name__)


class IndicF5Engine:
    """
    Thin wrapper around IndicF5.

    The model is loaded once and reused for all segments.
    """

    SAMPLE_RATE = 24000

    def __init__(
        self,
        model_path: str | Path,
    ) -> None:

        self._model_path = str(
            model_path
        )

        logger.info(
            "LOADING INDICF5 | model=%s",
            self._model_path,
        )

        self._model = AutoModel.from_pretrained(
            self._model_path,
            trust_remote_code=True,
        )

        logger.info(
            "INDICF5 LOADED | model=%s",
            self._model_path,
        )

    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str,
        output_path: Path,
    ) -> Path:

        if not text.strip():
            raise ValueError(
                "Target text cannot be empty."
            )

        if not reference_audio.is_file():
            raise FileNotFoundError(
                f"Reference audio does not exist: "
                f"{reference_audio}"
            )

        if not reference_text.strip():
            raise ValueError(
                "Reference text cannot be empty."
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "INDICF5 SYNTHESIS STARTED | "
            "text_length=%s | reference=%s",
            len(text),
            reference_audio,
        )

        result = None

        infer = getattr(
            self._model,
            "infer",
            None,
        )

        if callable(infer):

            try:
                result = infer(
                    text=text,
                    ref_audio_path=str(reference_audio),
                    ref_text=reference_text,
                )
            except TypeError:
                result = infer(
                    text,
                    str(reference_audio),
                    reference_text,
                )

        if result is None:

            try:
                result = self._model(
                    text,
                    ref_audio_path=str(
                        reference_audio
                    ),
                    ref_text=reference_text,
                )
            except TypeError:
                result = self._model(
                    text=text,
                    reference_audio=str(reference_audio),
                    reference_text=reference_text,
                )

        audio = self._extract_audio_samples(
            result
        )

        audio = self._normalize_audio(
            audio
        )

        if audio.size == 0:
            raise RuntimeError(
                "IndicF5 returned empty audio output."
            )

        sf.write(
            str(output_path),
            audio,
            self.SAMPLE_RATE,
            subtype="PCM_16",
        )

        logger.info(
            "INDICF5 SYNTHESIS COMPLETED | "
            "output=%s",
            output_path,
        )

        return output_path

    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_audio(
        audio,
    ) -> np.ndarray:

        audio = np.asarray(
            audio
        )

        if audio.dtype == np.int16:

            audio = (
                audio.astype(
                    np.float32
                )
                / 32768.0
            )

        else:

            audio = audio.astype(
                np.float32
            )

        # Remove DC offset.
        audio = (
            audio
            - np.mean(audio)
        )

        # Conservative peak normalization.
        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        if peak > 0.0:

            target_peak = 0.95

            if peak > target_peak:

                audio = (
                    audio
                    * (
                        target_peak
                        / peak
                    )
                )

        return np.clip(
            audio,
            -1.0,
            1.0,
        )

    @staticmethod
    def _extract_audio_samples(
        result,
    ):

        # Common remote-code outputs: dict, tuple/list, tensor-like, ndarray.
        if isinstance(result, dict):

            for key in (
                "audio",
                "wav",
                "speech",
                "generated_audio",
                "output",
            ):

                if key in result:
                    return result[key]

            raise RuntimeError(
                "IndicF5 output dictionary did not include audio samples."
            )

        if isinstance(result, (list, tuple)):

            if not result:
                raise RuntimeError(
                    "IndicF5 returned an empty output sequence."
                )

            return result[0]

        audio_attr = getattr(result, "audio", None)

        if audio_attr is not None:
            return audio_attr

        return result