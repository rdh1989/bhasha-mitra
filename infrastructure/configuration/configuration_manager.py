"""
Centralized configuration manager.

Loads all YAML configuration files during application startup.
"""

from pathlib import Path
from threading import Lock
from typing import Any

import yaml

from infrastructure.configuration.exceptions import ConfigurationError


class ConfigurationManager:
    """
    Thread-safe singleton configuration manager.
    """

    _instance = None
    _lock = Lock()

    CONFIG_FILES = {
        "app": "app.yaml",
        "providers": "providers.yaml",
        "models": "models.yaml",
        "logging": "logging.yaml",
        "languages": "languages.yaml",
        "security": "security.yaml",
    }

    def __new__(cls):

        with cls._lock:

            if cls._instance is None:

                cls._instance = super().__new__(cls)
                cls._instance._configs = {}
                cls._instance._initialized = False

        return cls._instance

    def initialize(self, config_directory: str | Path = "config") -> None:
        """
        Load every configuration file.
        """

        if self._initialized:
            return

        config_directory = Path(config_directory)

        if not config_directory.exists():
            raise ConfigurationError(
                f"Configuration directory not found: {config_directory}"
            )

        for section, filename in self.CONFIG_FILES.items():

            path = config_directory / filename

            if not path.exists():
                raise ConfigurationError(
                    f"Missing configuration file: {filename}"
                )

            try:

                with open(path, "r", encoding="utf-8") as file:

                    self._configs[section] = yaml.safe_load(file) or {}

            except yaml.YAMLError as error:

                raise ConfigurationError(
                    f"Invalid YAML in {filename}"
                ) from error

        self._initialized = True

    def reload(self) -> None:
        """
        Reload all configuration files.
        """

        self._initialized = False
        self._configs.clear()
        self.initialize()

    def get(self, section: str) -> dict[str, Any]:

        if section not in self._configs:

            raise ConfigurationError(
                f"Configuration '{section}' not loaded."
            )

        return self._configs[section]

    def get_value(
        self,
        section: str,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.get(section).get(key, default)

    @property
    def app(self):

        return self.get("app")

    @property
    def providers(self):

        return self.get("providers")

    @property
    def models(self):

        return self.get("models")

    @property
    def logging(self):

        return self.get("logging")

    @property
    def languages(self):

        return self.get("languages")

    @property
    def security(self):

        return self.get("security")

    def all(self) -> dict[str, dict[str, Any]]:
        """
        Return every loaded configuration.
        """

        return self._configs.copy()