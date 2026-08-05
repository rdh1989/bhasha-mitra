"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : translation_executor.py
Purpose     : Translation Execution Engine

Description
-----------
Executes translation using an already loaded translation model.

Responsibilities
----------------
• Retrieve loaded translation model
• Execute inference
• Return translated text

Notes
-----
Models are loaded during application startup by ModelManager.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from transformers import GenerationConfig

from ai.execution.base_executor import BaseExecutor
from ai.translation.models import (
    TranslationRequest,
    TranslationResult,
)


class TranslationExecutor(BaseExecutor):
    """
    Executes translation using the loaded model.
    """

    CATEGORY = "translation"

    def translate(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """
        Execute translation.
        """

        #
        # Get loaded model
        #
        model_bundle = self.get_model(
            category=self.CATEGORY,
            model="default",     # we'll remove this later
        )

        model = model_bundle["model"]
        tokenizer = model_bundle["tokenizer"]

        #
        # Tokenize
        #
        inputs = tokenizer(
            request.text,
            return_tensors="pt",
        )

        #
        # Generate
        #
        output = model.generate(
            **inputs,
            generation_config=GenerationConfig(
                max_new_tokens=512,
            ),
        )

        #
        # Decode
        #
        translated_text = tokenizer.batch_decode(
            output,
            skip_special_tokens=True,
        )[0]

        return TranslationResult(
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=None,
        )