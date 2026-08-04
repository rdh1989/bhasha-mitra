"""
YAML Configuration Service.

Loads application configuration from YAML and provides
typed access to configuration values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.application.interfaces.configuration_service import (
    ConfigurationService,
)


class YamlConfigurationService(ConfigurationService):
    """
    YAML-based implementation of ConfigurationService.
    """

    def __init__(
        self,
        config_file: Path,
    ) -> None:

        self._config_file = config_file

        with config_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            self._config: dict[str, Any] = yaml.safe_load(file) or {}

    # ==========================================================
    # Generic
    # ==========================================================

    def get(
        self,
        key: str,
        default: Any | None = None,
    ) -> Any:

        value: Any = self._config

        for part in key.split("."):

            if not isinstance(value, dict):
                return default

            if part not in value:
                return default

            value = value[part]

        return value

    def has(
        self,
        key: str,
    ) -> bool:

        return self.get(key) is not None

    # ==========================================================
    # Storage
    # ==========================================================

    @property
    def storage_root(self) -> Path:
        return Path(self.get("storage.root"))

    @property
    def upload_directory(self) -> Path:
        return Path(self.get("storage.uploads"))

    @property
    def output_directory(self) -> Path:
        return Path(self.get("storage.output"))

    @property
    def temp_directory(self) -> Path:
        return Path(self.get("storage.temp"))

    @property
    def cache_directory(self) -> Path:
        return Path(self.get("storage.cache"))

    # ==========================================================
    # AI Models
    # ==========================================================

    @property
    def whisper_model(self) -> str:
        return self.get("models.whisper")

    @property
    def translation_model(self) -> str:
        return self.get("models.translation")

    @property
    def tts_model(self) -> str:
        return self.get("models.tts")

    @property
    def language_detector(self) -> str:
        return self.get("models.language_detector")

    # ==========================================================
    # FFmpeg
    # ==========================================================

    @property
    def ffmpeg_path(self) -> Path:
        return Path(self.get("ffmpeg.path"))

    @property
    def ffprobe_path(self) -> Path:
        return Path(self.get("ffmpeg.ffprobe"))

    # ==========================================================
    # Application
    # ==========================================================

    @property
    def max_parallel_jobs(self) -> int:
        return int(self.get("application.max_parallel_jobs", 1))

    @property
    def max_retry_count(self) -> int:
        return int(self.get("application.max_retry_count", 3))

    @property
    def log_level(self) -> str:
        return self.get("application.log_level", "INFO")

    @property
    def debug(self) -> bool:
        return bool(self.get("application.debug", False))

    # ==========================================================
    # Utility
    # ==========================================================

    def reload(self) -> None:
        """
        Reload configuration from disk.
        """

        with self._config_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            self._config = yaml.safe_load(file) or {}