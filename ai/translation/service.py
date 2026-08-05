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

from ai.base.translation_provider import TranslationProvider
from ai.translation.adapter import TranslationAdapter
from ai.translation.models import (
    TranslationRequest,
    TranslationResult,
)
from ai.model_manager.manager import ModelManager
from ai.core.language_mapper import LANGUAGE_CODES as NLLB_LANGUAGE_MAP


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

        #
        # Tokenize input
        #
        inputs = tokenizer(
            request.text,
            return_tensors="pt",
            padding=True,
        )

        #
        # Generate translation
        #
        # translated = model.generate(
        #     **inputs,
        #     forced_bos_token_id=tokenizer.convert_tokens_to_ids(
        #         target_lang
        #     ),
        # )

        translated = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(
                target_lang
            ),
            max_new_tokens=256,
            num_beams=4,
            early_stopping=True,
        )

        #
        # Decode output
        #
        translated_text = tokenizer.batch_decode(
            translated,
            skip_special_tokens=True,
        )[0]

        #
        # Framework response
        #
        return TranslationResult(
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
        )


    def health_check(self) -> bool:
        """
        Check whether the translation model is loaded.
        """

        try:
            self._model_manager.get_default_model("translation")
            return True
        except Exception:
            return False