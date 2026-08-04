"""
FastText implementation of the LanguageProvider.
"""

from pathlib import Path

from app.providers.language.language_provider import LanguageProvider


class FastTextProvider(LanguageProvider):
    """
    Offline language detection using FastText.
    """

    def __init__(
        self,
        model_path: Path,
    ) -> None:
        """
        Initialize the FastText provider.

        Args:
            model_path:
                Path to the FastText language identification model.
        """
        self._model_path = model_path
        self._model = None

    def load(self) -> None:
        """
        Load the FastText model.

        Model loading will be implemented during the AI integration phase.
        """
        raise NotImplementedError(
            "FastText model loading is not implemented yet."
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