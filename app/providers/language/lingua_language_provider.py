"""
Lingua implementation of the Language Provider.

Package:
    lingua-language-detector
"""

from __future__ import annotations

from pathlib import Path

from lingua import (
    Language,
    LanguageDetectorBuilder,
)

from app.providers.language.base_language_provider import (
    BaseLanguageProvider,
)


class LinguaLanguageProvider(BaseLanguageProvider):
    """
    Offline language detection using Lingua.
    """

    def __init__(self) -> None:
        self._detector = (
            LanguageDetectorBuilder
            .from_all_languages()
            .build()
        )

    def detect(
        self,
        media_file: Path,
    ) -> str:
        """
        Detect the spoken language.

        NOTE
        ----
        Lingua detects language from text, not directly from
        audio or video.

        This implementation is intentionally left as a placeholder.
        The TranslationWorker should:

            Video
                ↓
            Extract Audio
                ↓
            ASR
                ↓
            Transcript
                ↓
            detect_text(transcript)

        Until then, this method is not implemented.
        """

        raise NotImplementedError(
            "Language detection requires transcript text."
        )

    def detect_text(
        self,
        text: str,
    ) -> str:
        """
        Detect language from text.

        Returns:
            ISO-639 language code.
        """

        if not text.strip():
            return "unknown"

        language = self._detector.detect_language_of(text)

        if language is None:
            return "unknown"

        return self._to_iso_code(language)

    @staticmethod
    def _to_iso_code(
        language: Language,
    ) -> str:
        """
        Convert Lingua Language enum to ISO code.
        """

        mapping = {
            Language.ENGLISH: "en",
            Language.HINDI: "hi",
            Language.MARATHI: "mr",
            Language.TAMIL: "ta",
            Language.TELUGU: "te",
            Language.KANNADA: "kn",
            Language.MALAYALAM: "ml",
            Language.GUJARATI: "gu",
            Language.BENGALI: "bn",
            Language.PUNJABI: "pa",
            Language.URDU: "ur",
        }

        return mapping.get(language, "unknown")