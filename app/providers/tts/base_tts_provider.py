"""
Base interface for Text-To-Speech providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSProvider(ABC):

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: str,
        output_file: Path,
    ) -> Path:
        """
        Generate speech audio.

        Returns:
            Generated audio path.
        """
        raise NotImplementedError