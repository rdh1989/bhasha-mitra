"""Indic Parler-TTS wrapper.

The model needs two tokenizers: its own (for the transcript "prompt") and the
flan-t5-large tokenizer (for the natural-language "description"/style prompt).
The flan-t5-large tokenizer is not bundled with the model, so it is downloaded
once from the Hugging Face Hub and cached under
models/tts/_description_tokenizer_cache for fully offline reuse afterwards.
"""
from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from app.config import TTS_DESCRIPTION_TOKENIZER_CACHE, TTS_DESCRIPTION_TOKENIZER_ID

logger = logging.getLogger(__name__)

# parler_tts unconditionally imports a `dac` package it doesn't actually need
# for our model (see app/_stubs/dac for details) - make the stub importable.
_STUBS_DIR = str(Path(__file__).resolve().parent.parent / "_stubs")
if _STUBS_DIR not in sys.path:
    sys.path.insert(0, _STUBS_DIR)


class TTSEngine:
    def __init__(self, model_dir):
        self._model_dir = str(model_dir)
        self._model = None
        self._tokenizer = None
        self._description_tokenizer = None
        self._sampling_rate = None
        self._lock = threading.Lock()

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            logger.info("Loading Indic Parler-TTS model from %s", self._model_dir)
            try:
                from parler_tts import ParlerTTSForConditionalGeneration
                from transformers import AutoTokenizer

                model = ParlerTTSForConditionalGeneration.from_pretrained(self._model_dir)
                model.eval()
                self._model = model
                self._tokenizer = AutoTokenizer.from_pretrained(self._model_dir)
                self._description_tokenizer = self._load_description_tokenizer()
                self._sampling_rate = model.config.sampling_rate
            except Exception:
                logger.exception("Failed to load TTS model from %s", self._model_dir)
                raise
            logger.info("TTS model loaded successfully (sampling_rate=%s)", self._sampling_rate)

    def unload(self) -> None:
        """Release the model and tokenizers so their memory can be freed."""
        with self._lock:
            if self._model is None:
                return
            self._model = None
            self._tokenizer = None
            self._description_tokenizer = None
            self._sampling_rate = None
        logger.info("TTS model unloaded")

    def _load_description_tokenizer(self):
        from transformers import AutoTokenizer

        if TTS_DESCRIPTION_TOKENIZER_CACHE.exists() and any(
            TTS_DESCRIPTION_TOKENIZER_CACHE.iterdir()
        ):
            logger.debug("Loading cached description tokenizer from %s", TTS_DESCRIPTION_TOKENIZER_CACHE)
            return AutoTokenizer.from_pretrained(str(TTS_DESCRIPTION_TOKENIZER_CACHE))
        # One-time download (small tokenizer files only), then cache locally.
        logger.info("Downloading description tokenizer '%s' (one-time, then cached offline)", TTS_DESCRIPTION_TOKENIZER_ID)
        try:
            tok = AutoTokenizer.from_pretrained(TTS_DESCRIPTION_TOKENIZER_ID)
        except Exception:
            logger.exception(
                "Failed to download description tokenizer '%s'. An internet connection is "
                "required the first time the TTS model runs.",
                TTS_DESCRIPTION_TOKENIZER_ID,
            )
            raise
        TTS_DESCRIPTION_TOKENIZER_CACHE.mkdir(parents=True, exist_ok=True)
        tok.save_pretrained(str(TTS_DESCRIPTION_TOKENIZER_CACHE))
        logger.info("Description tokenizer cached at %s", TTS_DESCRIPTION_TOKENIZER_CACHE)
        return tok

    @property
    def sampling_rate(self) -> int:
        self.ensure_loaded()
        return self._sampling_rate

    def synthesize(self, text: str, description: str):
        """Returns a 1-D float32 numpy array at self.sampling_rate."""
        self.ensure_loaded()
        import torch

        max_new_tokens = self._estimate_max_new_tokens(text)
        logger.debug(
            "Synthesizing speech for text of length %d (max_new_tokens=%d)", len(text), max_new_tokens
        )
        try:
            description_ids = self._description_tokenizer(description, return_tensors="pt")
            prompt_ids = self._tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                generation = self._model.generate(
                    input_ids=description_ids.input_ids,
                    attention_mask=description_ids.attention_mask,
                    prompt_input_ids=prompt_ids.input_ids,
                    prompt_attention_mask=prompt_ids.attention_mask,
                    max_new_tokens=max_new_tokens,
                )
        except Exception:
            logger.exception("TTS synthesis failed for text: %r", text)
            raise
        return generation.cpu().numpy().squeeze()

    @staticmethod
    def _estimate_max_new_tokens(text: str) -> int:
        """Cap generation length based on the input text instead of relying on
        the model's default (2610 steps, ~30s of audio). Without this, the
        model's sampling occasionally rambles well past what a short segment
        needs, and every extra decode step is a full forward pass on CPU."""
        frame_rate = 86  # matches the bundled DAC codec (44100 Hz / 512 hop length)
        chars_per_second = 11  # conservative speaking-rate estimate across scripts
        min_tokens, max_tokens = 40, 1400
        estimated_seconds = max(1.0, len(text) / chars_per_second)
        return int(min(max_tokens, max(min_tokens, estimated_seconds * frame_rate * 1.8)))
