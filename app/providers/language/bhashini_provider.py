"""
Bhashini implementation of the LanguageProvider.
"""

from pathlib import Path

from app.providers.language.language_provider import LanguageProvider


class BhashiniProvider(LanguageProvider):
    """
    Language detection using the Bhashini platform.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
    ) -> None:
        """
        Initialize the Bhashini provider.

        Args:
            endpoint:
                Bhashini API endpoint.
            api_key:
                Authentication key.
        """
        self._endpoint = endpoint
        self._api_key = api_key

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
            "Bhashini language detection is not implemented yet."
        )