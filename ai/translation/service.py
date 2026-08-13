"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Translation Service

Description:
    Provides text translation using the configured Translation provider.

Design Patterns:
    • Strategy
    • Dependency Injection

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

import re
import time
import logging

import torch

from ai.base.translation_provider import TranslationProvider
from ai.translation.adapter import TranslationAdapter
from ai.translation.models import (
    TranslationRequest,
    TranslationResult,
)
from ai.model_manager.manager import ModelManager
from ai.core.language_mapper import LANGUAGE_CODES as NLLB_LANGUAGE_MAP


logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translation orchestration service.

    Responsibilities
    ----------------
    • Accept translation requests.
    • Delegate translation to configured provider.
    • Normalize provider output.
    • Return framework models.
    """

    # num_beams=1 (greedy) is fastest but measurably lower quality for NLLB.
    # 2 beams gives a real accuracy gain while staying cheap; batching all
    # chunks into one generate() call below offsets most of the added cost.
    NUM_BEAMS = 2

    def __init__(
        self,
        adapter: TranslationAdapter,
    ) -> None:

        self._adapter = adapter
        self._model_manager = ModelManager()

    def translate(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """
        Translate text using the already loaded translation model.
        """

        #
        # Get loaded model bundle
        #
        try:

            model_bundle = self._model_manager.get_default_model(
                "translation"
            )

        except RuntimeError as exc:

            if "is not loaded" not in str(exc):
                raise

            metadata = self._model_manager.get_default_metadata(
                "translation"
            )

            logger.info(
                "Loading default translation model on demand | model=%s",
                metadata.get("model"),
            )

            self._model_manager.load_model(
                category="translation",
                model=metadata["model"],
            )

            model_bundle = self._model_manager.get_default_model(
                "translation"
            )

        model = model_bundle["model"]
        tokenizer = model_bundle["tokenizer"]

        #
        # Resolve NLLB language codes
        #
        try:

            source_lang = NLLB_LANGUAGE_MAP[
                request.source_language.lower()
            ]

            target_lang = NLLB_LANGUAGE_MAP[
                request.target_language.lower()
            ]

        except KeyError as exc:

            raise ValueError(
                f"Unsupported language: {exc.args[0]}"
            )

        #
        # Configure tokenizer
        #
        tokenizer.src_lang = source_lang

        start_time = time.perf_counter()

        # Split long input into smaller chunks so each generation pass stays
        # within a reasonable sequence length.
        chunks = [
            chunk.strip()
            for chunk in self._chunk_text(request.text)
            if chunk.strip()
        ]

        if not chunks:
            translated_text = ""
        else:

            # Batch every chunk into a single generate() call instead of one
            # call per chunk: one batched forward pass beats N sequential
            # ones (fewer kernel/model dispatch round-trips).
            inputs = tokenizer(
                chunks,
                return_tensors="pt",
                padding=True,
            )

            # A fixed token budget truncates longer chunks: Devanagari output
            # from NLLB commonly needs more tokens than the English input has
            # words. Scale the budget with the longest chunk in the batch.
            max_new_tokens = min(
                512,
                max(90, inputs["input_ids"].shape[-1] * 3),
            )

            with torch.inference_mode():

                translated = model.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.convert_tokens_to_ids(
                        target_lang
                    ),
                    # NLLB's generation_config.json ships a default max_length=200
                    # that conflicts with max_new_tokens; disable it explicitly.
                    max_length=None,
                    max_new_tokens=max_new_tokens,
                    num_beams=self.NUM_BEAMS,
                    do_sample=False,
                    early_stopping=True,
                    repetition_penalty=1.15,
                    no_repeat_ngram_size=3,
                    length_penalty=1.0,
                )

            translated_parts = tokenizer.batch_decode(
                translated,
                skip_special_tokens=True,
            )

            translated_text = " ".join(
                part.strip() for part in translated_parts
            ).strip()

        #
        # Framework response
        #
        return TranslationResult(
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=round(
                max(0.0, 1.0 - ((time.perf_counter() - start_time) / 5.0)),
                3,
            ),
        )


    def _chunk_text(self, text: str, max_chars: int = 400) -> list[str]:
        """
        Split long translation input into smaller chunks to keep each generation
        step fast and reduce end-to-end translation latency.
        """

        if not text:
            return []

        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= max_chars:
            return [normalized]

        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if not sentence:
                continue
            candidate = f"{current} {sentence}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks or [normalized]

    def health_check(self) -> bool:
        """
        Check whether the translation model is loaded.
        """

        try:
            self._model_manager.get_default_model("translation")
            return True
        except Exception:
            return False