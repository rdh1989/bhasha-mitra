"""
Base interface for translation providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTranslationProvider(ABC):
    """
    Contract for text translation providers.
    """

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """
        Translate text.

        Returns:
            Translated text.
        """
        raise NotImplementedError