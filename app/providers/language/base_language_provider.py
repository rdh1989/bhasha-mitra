"""
Base interface for language detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseLanguageProvider(ABC):

    @abstractmethod
    def detect(
        self,
        media_file: Path,
    ) -> str:
        """
        Detect language from media.

        Returns:
            ISO language code.
        """
        raise NotImplementedError