"""
Filesystem implementation of ConfigRepository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.application.interfaces.config_repository import ConfigRepository


class FileConfigRepository(ConfigRepository):
    """
    Reads and writes YAML configuration files.
    """

    def __init__(
        self,
        config_directory: Path,
    ) -> None:

        self._directory = config_directory

        self._config: dict[str, Any] = {}

        self.load()

    # ---------------------------------------------------------
    # Generic
    # ---------------------------------------------------------

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

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:

        parts = key.split(".")

        config = self._config

        for part in parts[:-1]:

            config = config.setdefault(
                part,
                {},
            )

        config[parts[-1]] = value

    def has(
        self,
        key: str,
    ) -> bool:

        return self.get(key) is not None

    def remove(
        self,
        key: str,
    ) -> None:

        parts = key.split(".")

        config = self._config

        for part in parts[:-1]:

            if part not in config:
                return

            config = config[part]

        config.pop(
            parts[-1],
            None,
        )

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def load(
        self,
    ) -> None:

        self._config.clear()

        for file in self._directory.glob("*.yaml"):

            with file.open(
                "r",
                encoding="utf-8",
            ) as stream:

                self._config[file.stem] = (
                    yaml.safe_load(stream) or {}
                )

    def reload(
        self,
    ) -> None:

        self.load()

    def save(
        self,
    ) -> None:

        for section, values in self._config.items():

            file = self._directory / f"{section}.yaml"

            with file.open(
                "w",
                encoding="utf-8",
            ) as stream:

                yaml.safe_dump(
                    values,
                    stream,
                    allow_unicode=True,
                    sort_keys=False,
                )

    # ---------------------------------------------------------
    # Export
    # ---------------------------------------------------------

    def as_dict(
        self,
    ) -> dict[str, Any]:

        return dict(self._config)

    def clear(
        self,
    ) -> None:

        self._config.clear()