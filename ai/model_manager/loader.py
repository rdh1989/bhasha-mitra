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

import importlib.machinery
import os
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ai.core.exceptions import (
    ModelLoadError,
    ModelNotFoundError,
)
from ai.model_manager.registry import ModelRegistry


@contextmanager
def _temporary_torchaudio_stub() -> Any:
    """
    Temporarily inject a torchaudio stub for text-only transformers loads.

    This avoids loading a broken torchaudio native extension while still
    allowing translation models to initialize.
    """

    had_existing = "torchaudio" in sys.modules
    existing_module = sys.modules.get("torchaudio")

    fake_module = types.ModuleType("torchaudio")
    fake_module.__spec__ = importlib.machinery.ModuleSpec(
        "torchaudio",
        loader=None,
    )
    sys.modules["torchaudio"] = fake_module

    try:
        yield
    finally:
        if had_existing:
            sys.modules["torchaudio"] = existing_module
        else:
            sys.modules.pop("torchaudio", None)


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
        configured_path = metadata.get("path")

        if not configured_path:
            raise ModelLoadError("Model path is missing from metadata.")

        model_path = Path(configured_path)
        if not model_path.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            model_path = (repo_root / model_path).resolve()

        if not model_path.exists():
            raise ModelLoadError(
                f"Model path does not exist: {model_path}"
            )

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

            with _temporary_torchaudio_stub():

                try:
                    import transformers
                except ImportError as exc:
                    raise ModelLoadError(
                        "Transformers is required to load the NLLB model."
                    ) from exc

                if (
                    hasattr(transformers, "NllbTokenizer")
                    and hasattr(transformers, "NllbForConditionalGeneration")
                ):
                    tokenizer = transformers.NllbTokenizer.from_pretrained(
                        str(model_path),
                        local_files_only=True,
                    )
                    model = transformers.NllbForConditionalGeneration.from_pretrained(
                        str(model_path),
                        local_files_only=True,
                    )
                    return {
                        "model": model,
                        "tokenizer": tokenizer,
                    }

                expected_files = [
                    "config.json",
                    "generation_config.json",
                    "pytorch_model.bin",
                    "tokenizer_config.json",
                ]
                missing_files = [
                    file_name
                    for file_name in expected_files
                    if not (model_path / file_name).exists()
                ]

                if missing_files:
                    raise ModelLoadError(
                        f"NLLB model directory is incomplete: {model_path}. "
                        f"Missing files: {', '.join(missing_files)}"
                    )

                import torch
                from transformers import (
                    AutoTokenizer,
                    AutoModelForSeq2SeqLM,
                )

                tokenizer = AutoTokenizer.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                )

                use_safetensors = (model_path / "model.safetensors").exists()

                model = AutoModelForSeq2SeqLM.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                    low_cpu_mem_usage=True,
                    use_safetensors=use_safetensors,
                    dtype=torch.float32,
                )

                try:
                    model.to("cpu")
                except Exception:
                    pass

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

