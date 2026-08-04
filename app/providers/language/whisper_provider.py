"""
Whisper implementation of the LanguageProvider.
"""

from pathlib import Path

from app.providers.language.language_provider import LanguageProvider


class WhisperProvider(LanguageProvider):
    """
    Language detection using Whisper.
    """

    def __init__(
        self,
        model_name: str = "base",
    ) -> None:
        """
        Initialize the Whisper provider.

        Args:
            model_name:
                Whisper model name.
        """
        self._model_name = model_name
        self._model = None

    def load(self) -> None:
        """
        Load the Whisper model.

        Model loading will be implemented during the AI integration phase.
        """
        raise NotImplementedError(
            "Whisper model loading is not implemented yet."
        )

    def detect(
        self,
        media_file: Path,
    ) -> str:
        """
        Detect the spoken language from a media file.

        Args:
            media_file:
                Input audio or video file.

        Returns:
            ISO 639-1 language code.
        """
        raise NotImplementedError(
            "Language detection is not implemented yet."
        )