"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : loader.py
Purpose     : AI Model Loader

Description:
    Responsible for loading and unloading AI models.

Design Pattern:
    Loader Pattern

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ai.core.exceptions import (
    ModelLoadError,
    ModelNotFoundError,
)
from ai.model_manager.registry import ModelRegistry


class ModelLoader:
    """
    Responsible for loading AI models into memory.

    Responsibilities
    ----------------
    • Load models from filesystem
    • Unload models

    Notes
    -----
    This class does NOT:

    • Cache models
    • Read manifest
    • Validate models
    """

    def __init__(
        self,
        registry: ModelRegistry,
    ) -> None:
        self._registry = registry

    def load(
        self,
        category: str,
        model: str,
    ) -> Any:
        """
        Load a model.

        Parameters
        ----------
        category : str
            AI category (asr, translation, tts, ...)

        model : str
            Model name

        Returns
        -------
        Any
            Loaded model instance.
        """

        if not self._registry.exists(category, model):
            raise ModelNotFoundError(
                f"Model '{category}:{model}' is not registered."
            )

        metadata = self._registry.get(category, model)

        try:
            return self._load_model(metadata)

        except Exception as exc:
            raise ModelLoadError(
                f"Failed to load model "
                f"'{category}:{model}'."
            ) from exc

    def unload(
        self,
        model: Any,
    ) -> None:
        """
        Unload model.
        """

        del model

    def _load_model(
        self,
        metadata: dict,
    ) -> Any:
        """
        Provider specific loading.

        Notes
        -----
        This method dispatches loading based on provider.
        """

        provider = metadata["provider"]
        model_path = Path(metadata["path"])

        #
        # Faster Whisper
        #
        if provider == "faster_whisper":

            from faster_whisper import WhisperModel

            # return WhisperModel(
            #     str(model_path),
            #     device="cpu",
            #     compute_type="int8",
            # )

            return WhisperModel(
                str(model_path),
                device="cpu",
                compute_type="int8",
                cpu_threads=os.cpu_count(),
            )

        #
        # MarianMT
        #
        if provider == "marianmt":

            from transformers import (
                MarianMTModel,
                MarianTokenizer,
            )

            tokenizer = MarianTokenizer.from_pretrained(
                str(model_path),
                local_files_only=True,
            )

            model = MarianMTModel.from_pretrained(
                str(model_path),
                local_files_only=True,
            )

            return {
                "model": model,
                "tokenizer": tokenizer,
            }

                #
        # IndicTrans2
        #
        if provider == "indictrans2":
            from transformers import (
                AutoTokenizer,
                AutoModelForSeq2SeqLM,
            )

            tokenizer = AutoTokenizer.from_pretrained(
                str(model_path),
                trust_remote_code=True,
                local_files_only=True,
            )

            model = AutoModelForSeq2SeqLM.from_pretrained(
                str(model_path),
                trust_remote_code=True,
                local_files_only=True,
            )

            return {
                "model": model,
                "tokenizer": tokenizer,
            }

        if provider == "nllb":

            from transformers import (
                AutoTokenizer,
                AutoModelForSeq2SeqLM,
            )

            tokenizer = AutoTokenizer.from_pretrained(
                str(model_path),
                local_files_only=True,
            )

            model = AutoModelForSeq2SeqLM.from_pretrained(
                str(model_path),
                local_files_only=True,
            )

            return {
                "model": model,
                "tokenizer": tokenizer,
            }

        #
        # Piper
        #
        if provider == "piper":

            from piper import PiperVoice

            #
            # Manifest path points to the Piper voice directory.
            #
            onnx_models = list(
                model_path.glob("*.onnx")
            )

            if not onnx_models:
                raise ModelLoadError(
                    f"No Piper ONNX model found in: {model_path}"
                )

            return PiperVoice.load(
                str(onnx_models[0])
            )

        #
        # Lingua
        #
        if provider == "lingua":
            raise NotImplementedError(
                "Lingua loader not implemented."
            )

        raise ModelLoadError(
            f"Unsupported provider: {provider}"
        )


