"""
Base interface for subtitle generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseSubtitleProvider(ABC):

    @abstractmethod
    def generate(
        self,
        text: str,
        output_file: Path,
    ) -> Path:
        """
        Generate subtitle (.srt).

        Returns:
            Subtitle file.
        """
        raise NotImplementedError