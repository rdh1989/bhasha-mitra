"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Text-to-Speech Service
===============================================================================
"""

from __future__ import annotations

import wave

from ai.model_manager.manager import ModelManager
from ai.tts.adapter import TTSAdapter
from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)


class TTSService:
    """
    Text-to-Speech orchestration service.

    Responsibilities
    ----------------
    • Accept speech synthesis requests.
    • Use already loaded TTS model.
    • Generate audio.
    • Return framework SpeechResult.
    """

    def __init__(
        self,
        adapter: TTSAdapter,
    ) -> None:

        self._adapter = adapter
        self._model_manager = ModelManager()

    # ------------------------------------------------------------------
    # Synthesize
    # ------------------------------------------------------------------

    def synthesize(
        self,
        request: SpeechRequest,
    ) -> SpeechResult:
        """
        Generate speech using the already loaded TTS model.
        """

        if not request.text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        # Get already loaded TTS model
        tts_model = (
            self._model_manager.get_default_model(
                "tts"
            )
        )

        # Ensure output directory exists
        request.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Create WAV with required audio parameters
        with wave.open(
            str(request.output_path),
            "wb",
        ) as wav_file:

            if request.length_scale is not None:
                from piper import SynthesisConfig

                tts_model.synthesize_wav(
                    request.text,
                    wav_file,
                    syn_config=SynthesisConfig(
                        length_scale=request.length_scale,
                    ),
                )
            else:
                tts_model.synthesize_wav(
                    request.text,
                    wav_file,
                )

        # Read generated WAV metadata
        with wave.open(
            str(request.output_path),
            "rb",
        ) as wav_file:

            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()

        duration = (
            frame_count / sample_rate
            if sample_rate
            else None
        )

        configured_voice = str(
            self._model_manager.get_default_metadata("tts").get(
                "model",
                "",
            )
        ).strip()

        if not configured_voice:
            raise RuntimeError(
                "Configured TTS voice is missing from model metadata."
            )

        #
        # Framework response
        #
        
        return SpeechResult(
            audio_path=request.output_path,
            language=request.language,
            voice=configured_voice,
            sample_rate=sample_rate,
            duration=duration,
        )


    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(
        self,
    ) -> bool:

        try:

            self._model_manager.get_default_model(
                "tts"
            )

            return True

        except Exception:

            return False

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(
        self,
    ) -> None:
        """
        Model lifecycle is handled by ModelManager.
        """

        pass