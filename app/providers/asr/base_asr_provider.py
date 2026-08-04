"""
Base interface for Automatic Speech Recognition (ASR) providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseASRProvider(ABC):
    """
    Contract for speech-to-text providers.
    """

    @abstractmethod
    def transcribe(
        self,
        audio_file: Path,
        language: str | None = None,
    ) -> str:
        """
        Convert speech into text.

        Args:
            audio_file: Input audio file.
            language: Optional language hint.

        Returns:
            Transcribed text.
        """
        raise NotImplementedError