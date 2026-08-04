"""
NLLB Translation Provider.

Offline translation using CTranslate2 + SentencePiece.

Supported initially:
    English -> Marathi

Can later be extended to all NLLB languages.
"""

from __future__ import annotations

from pathlib import Path

import ctranslate2
import sentencepiece as spm

from app.providers.translation.base_translation_provider import (
    BaseTranslationProvider,
)


class NLLBTranslationProvider(BaseTranslationProvider):
    """
    Offline NLLB translation provider.
    """

    def __init__(
        self,
        model_path: Path,
        sentencepiece_model: Path,
        device: str = "cpu",
    ) -> None:

        self._translator = ctranslate2.Translator(
            str(model_path),
            device=device,
        )

        self._tokenizer = spm.SentencePieceProcessor(
            model_file=str(sentencepiece_model),
        )

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """
        Translate text.

        Args:
            text:
                Source text.

            source_language:
                ISO language code.

            target_language:
                ISO language code.

        Returns:
            Translated text.
        """

        if not text.strip():
            return ""

        source_token = self._language_token(
            source_language
        )

        target_token = self._language_token(
            target_language
        )

        tokens = self._tokenizer.encode(
            text,
            out_type=str,
        )

        source = [
            source_token,
            *tokens,
            "</s>",
        ]

        result = self._translator.translate_batch(
            [source],
            target_prefix=[[target_token]],
        )

        output_tokens = result[0].hypotheses[0]

        filtered = [
            token
            for token in output_tokens
            if not token.startswith("__")
            and token != "</s>"
        ]

        return self._tokenizer.decode(filtered)

    @staticmethod
    def _language_token(
        language: str,
    ) -> str:
        """
        Convert ISO code to NLLB language token.
        """

        mapping = {
            "en": "__eng_Latn__",
            "mr": "__mar_Deva__",
            "hi": "__hin_Deva__",
            "ta": "__tam_Taml__",
            "te": "__tel_Telu__",
            "kn": "__kan_Knda__",
            "ml": "__mal_Mlym__",
            "gu": "__guj_Gujr__",
            "bn": "__ben_Beng__",
            "pa": "__pan_Guru__",
            "ur": "__urd_Arab__",
        }

        try:
            return mapping[language]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported language: {language}"
            ) from exc