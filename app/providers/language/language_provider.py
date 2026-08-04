"""
Contract for language detection providers.
"""

from abc import ABC
from abc import abstractmethod

from pathlib import Path


class LanguageProvider(ABC):
    """
    Contract for language detection providers.
    """

    @abstractmethod
    def detect(
        self,
        media_file: Path,
    ) -> str:
        """
        Detect the language spoken in a media file.

        Args:
            media_file:
                Input audio or video file.

        Returns:
            ISO language code.

        Example:
            "en"
            "hi"
            "mr"
        """
        raise NotImplementedError