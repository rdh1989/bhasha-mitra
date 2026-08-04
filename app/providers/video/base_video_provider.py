"""
Base interface for video processing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseVideoProvider(ABC):

    @abstractmethod
    def extract_audio(
        self,
        video_file: Path,
        output_audio: Path,
    ) -> Path:
        """
        Extract audio from video.
        """
        raise NotImplementedError

    @abstractmethod
    def merge_audio(
        self,
        video_file: Path,
        audio_file: Path,
        output_video: Path,
    ) -> Path:
        """
        Merge translated audio into video.
        """
        raise NotImplementedError

    @abstractmethod
    def add_subtitles(
        self,
        video_file: Path,
        subtitle_file: Path,
        output_video: Path,
    ) -> Path:
        """
        Burn subtitles into video.
        """
        raise NotImplementedError