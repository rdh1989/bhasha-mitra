"""
Configuration Service Contract.

Provides application-wide access to configuration settings.
The Application layer depends only on this abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ConfigurationService(ABC):
    """
    Application configuration abstraction.
    """

    # ==========================================================
    # Generic
    # ==========================================================

    @abstractmethod
    def get(
        self,
        key: str,
        default: Any | None = None,
    ) -> Any:
        """
        Return a configuration value.

        Example:
            get("storage.root")
            get("models.asr")
        """

    @abstractmethod
    def has(
        self,
        key: str,
    ) -> bool:
        """
        Returns True if the configuration key exists.
        """

    # ==========================================================
    # Storage
    # ==========================================================

    @property
    @abstractmethod
    def storage_root(self) -> Path:
        """Storage root directory."""

    @property
    @abstractmethod
    def upload_directory(self) -> Path:
        """Upload directory."""

    @property
    @abstractmethod
    def output_directory(self) -> Path:
        """Output directory."""

    @property
    @abstractmethod
    def temp_directory(self) -> Path:
        """Temporary directory."""

    @property
    @abstractmethod
    def cache_directory(self) -> Path:
        """Cache directory."""

    # ==========================================================
    # AI Models
    # ==========================================================

    @property
    @abstractmethod
    def whisper_model(self) -> str:
        """Whisper model name/path."""

    @property
    @abstractmethod
    def translation_model(self) -> str:
        """Translation model name/path."""

    @property
    @abstractmethod
    def tts_model(self) -> str:
        """Text-to-Speech model."""

    @property
    @abstractmethod
    def language_detector(self) -> str:
        """Language detection model."""

    # ==========================================================
    # FFmpeg
    # ==========================================================

    @property
    @abstractmethod
    def ffmpeg_path(self) -> Path:
        """FFmpeg executable."""

    @property
    @abstractmethod
    def ffprobe_path(self) -> Path:
        """FFprobe executable."""

    # ==========================================================
    # Application
    # ==========================================================

    @property
    @abstractmethod
    def max_parallel_jobs(self) -> int:
        """Maximum concurrent jobs."""

    @property
    @abstractmethod
    def max_retry_count(self) -> int:
        """Maximum retry attempts."""

    @property
    @abstractmethod
    def log_level(self) -> str:
        """Application log level."""

    @property
    @abstractmethod
    def debug(self) -> bool:
        """Debug mode."""