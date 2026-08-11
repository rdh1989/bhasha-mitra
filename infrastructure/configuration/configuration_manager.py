"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    configuration_manager.py

Layer:
    Infrastructure / Configuration

Description:
    Loads and provides centralized access to application configuration.

Responsibilities:
    - Load static YAML configuration
    - Load runtime/model manifest
    - Load packaged application.json
    - Load writable user application.json
    - Persist writable application configuration
    - Provide centralized configuration access
    - Support application configuration updates

Configuration model:
    Packaged:
        config/application.json

    Runtime:
        <user application data>/BhashaMitra/application.json

    The packaged application.json is the default/template configuration.
    The writable application.json contains the user configuration.

Does Not:
    - Provide fallback output paths
    - Provide fallback database paths
    - Modify the packaged application.json
    - Validate filesystem accessibility

===============================================================================
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

import yaml

from infrastructure.configuration.exceptions import (
    ConfigurationError,
)


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

    MANIFEST_FILE = "manifest.json"
    APPLICATION_CONFIG_FILE = "application.json"

    APPLICATION_NAME = "BhashaMitra"

    REQUIRED_APPLICATION_CONFIG = {
        "output_path",
        "database_path",
    }

    def __new__(cls):

        with cls._lock:

            if cls._instance is None:

                cls._instance = super().__new__(
                    cls
                )

                cls._instance._configs = {}
                cls._instance._initialized = False
                cls._instance._config_directory = None
                cls._instance._runtime_config_path = None

        return cls._instance

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(
        self,
        config_directory: str | Path = "config",
    ) -> None:
        """
        Load all static configuration and application configuration.

        The packaged application.json is mandatory.

        The writable runtime application.json is optional on first launch.
        """

        if self._initialized:
            return

        project_root = Path(__file__).resolve().parents[2]

        config_directory = Path(
            config_directory
        ).expanduser()

        if not config_directory.is_absolute():
            config_directory = (
                project_root / config_directory
            ).resolve()

        if not config_directory.exists():

            raise ConfigurationError(
                f"Configuration directory not found: "
                f"{config_directory}"
            )

        if not config_directory.is_dir():

            raise ConfigurationError(
                f"Configuration path is not a directory: "
                f"{config_directory}"
            )

        self._config_directory = config_directory

        self._load_yaml_configuration()
        self._load_manifest()
        self._load_application_configuration()

        self._initialized = True

    # =========================================================================
    # YAML
    # =========================================================================

    def _load_yaml_configuration(
        self,
    ) -> None:
        """
        Load all static YAML configuration files.
        """

        if self._config_directory is None:

            raise ConfigurationError(
                "Configuration directory is not initialized."
            )

        for section, filename in self.CONFIG_FILES.items():

            path = (
                self._config_directory
                / filename
            )

            if not path.is_file():

                raise ConfigurationError(
                    f"Missing configuration file: "
                    f"{filename}"
                )

            try:

                with path.open(
                    "r",
                    encoding="utf-8",
                ) as file:

                    self._configs[section] = (
                        yaml.safe_load(file)
                        or {}
                    )

            except OSError as error:

                raise ConfigurationError(
                    f"Unable to read configuration file: "
                    f"{filename}"
                ) from error

            except yaml.YAMLError as error:

                raise ConfigurationError(
                    f"Invalid YAML in {filename}"
                ) from error

    # =========================================================================
    # Manifest
    # =========================================================================

    def _load_manifest(
        self,
    ) -> None:
        """
        Load runtime/model manifest.
        """

        if self._config_directory is None:

            raise ConfigurationError(
                "Configuration directory is not initialized."
            )

        manifest_path = (
            self._config_directory
            / self.MANIFEST_FILE
        )

        if not manifest_path.is_file():

            raise ConfigurationError(
                f"Missing configuration file: "
                f"{self.MANIFEST_FILE}"
            )

        try:

            with manifest_path.open(
                "r",
                encoding="utf-8",
            ) as file:

                self._configs["manifest"] = json.load(
                    file
                )

        except OSError as error:

            raise ConfigurationError(
                f"Unable to read "
                f"{self.MANIFEST_FILE}"
            ) from error

        except json.JSONDecodeError as error:

            raise ConfigurationError(
                f"Invalid JSON in "
                f"{self.MANIFEST_FILE}"
            ) from error

    # =========================================================================
    # Application configuration
    # =========================================================================

    def _load_application_configuration(
        self,
    ) -> None:
        """
        Load packaged application configuration and override it with
        writable user configuration when available.
        """

        if self._config_directory is None:

            raise ConfigurationError(
                "Configuration directory is not initialized."
            )

        packaged_path = (
            self._config_directory
            / self.APPLICATION_CONFIG_FILE
        )

        if not packaged_path.is_file():

            raise ConfigurationError(
                f"Missing configuration file: "
                f"{self.APPLICATION_CONFIG_FILE}"
            )

        try:

            with packaged_path.open(
                "r",
                encoding="utf-8",
            ) as file:

                packaged_config = json.load(
                    file
                )

        except OSError as error:

            raise ConfigurationError(
                f"Unable to read "
                f"{self.APPLICATION_CONFIG_FILE}"
            ) from error

        except json.JSONDecodeError as error:

            raise ConfigurationError(
                f"Invalid JSON in "
                f"{self.APPLICATION_CONFIG_FILE}"
            ) from error

        if not isinstance(
            packaged_config,
            dict,
        ):

            raise ConfigurationError(
                f"{self.APPLICATION_CONFIG_FILE} "
                "must contain a JSON object."
            )

        application_config = dict(
            packaged_config
        )

        self._runtime_config_path = (
            self._get_runtime_config_path()
        )

        if self._runtime_config_path.is_file():

            try:

                with self._runtime_config_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:

                    runtime_config = json.load(
                        file
                    )

            except OSError as error:

                raise ConfigurationError(
                    "Unable to read writable application "
                    "configuration."
                ) from error

            except json.JSONDecodeError as error:

                raise ConfigurationError(
                    "Writable application configuration "
                    "contains invalid JSON."
                ) from error

            if not isinstance(
                runtime_config,
                dict,
            ):

                raise ConfigurationError(
                    "Writable application configuration "
                    "must contain a JSON object."
                )

            application_config.update(
                runtime_config
            )

        self._configs["application"] = (
            application_config
        )

    def _get_runtime_config_path(
        self,
    ) -> Path:
        """
        Return the writable runtime application configuration path.

        Windows:
            %LOCALAPPDATA%/BhashaMitra/application.json

        Other platforms:
            ~/.BhashaMitra/application.json
        """

        local_app_data = os.environ.get(
            "LOCALAPPDATA"
        )

        if local_app_data:

            root = Path(
                local_app_data
            )

        else:

            root = (
                Path.home()
                / ".BhashaMitra"
            )

        return (
            root
            / self.APPLICATION_NAME
            / self.APPLICATION_CONFIG_FILE
        )

    # =========================================================================
    # Application configuration state
    # =========================================================================

    def is_application_configured(
        self,
    ) -> bool:
        """
        Return True when required application paths are configured.
        """

        application = self._configs.get(
            "application",
            {},
        )

        return all(
            isinstance(
                application.get(key),
                str,
            )
            and bool(
                application.get(key).strip()
            )
            for key in self.REQUIRED_APPLICATION_CONFIG
        )

    def is_configuration_source_accessible(
        self,
    ) -> bool:
        """
        Return True when the packaged configuration source
        is accessible.

        The writable runtime application configuration is optional.
        """

        if not self._initialized:
            return False

        if self._config_directory is None:
            return False

        if not self._config_directory.is_dir():
            return False

        required_files = (
            *self.CONFIG_FILES.values(),
            self.MANIFEST_FILE,
            self.APPLICATION_CONFIG_FILE,
        )

        return all(
            (
                self._config_directory / filename
            ).is_file()
            for filename in required_files
        )

    # =========================================================================
    # Application configuration persistence
    # =========================================================================

    def configure_application(
        self,
        output_path: str | Path,
        database_path: str | Path,
    ) -> None:
        """
        Persist the user-selected application configuration.

        The packaged configuration remains unchanged.
        """

        output = str(
            Path(output_path).expanduser()
        ).strip()

        database = str(
            Path(database_path).expanduser()
        ).strip()

        if not output:

            raise ConfigurationError(
                "Output path cannot be empty."
            )

        if not database:

            raise ConfigurationError(
                "Database path cannot be empty."
            )

        current = dict(
            self._configs.get(
                "application",
                {},
            )
        )

        current["output_path"] = output
        current["database_path"] = database

        self._save_runtime_configuration(
            current
        )

        self._configs["application"] = current

    def update_application(
        self,
        *,
        output_path: str | Path | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        """
        Update the writable application configuration.

        Only supplied values are changed.
        """

        current = dict(
            self._configs.get(
                "application",
                {},
            )
        )

        if output_path is not None:

            output = str(
                Path(output_path).expanduser()
            ).strip()

            if not output:

                raise ConfigurationError(
                    "Output path cannot be empty."
                )

            current["output_path"] = output

        if database_path is not None:

            database = str(
                Path(database_path).expanduser()
            ).strip()

            if not database:

                raise ConfigurationError(
                    "Database path cannot be empty."
                )

            current["database_path"] = database

        self._save_runtime_configuration(
            current
        )

        self._configs["application"] = current

    def _save_runtime_configuration(
        self,
        configuration: dict[str, Any],
    ) -> None:
        """
        Save application configuration to the writable runtime location.

        The packaged application.json is never modified.
        """

        if self._runtime_config_path is None:

            raise ConfigurationError(
                "Runtime configuration path is not initialized."
            )

        try:

            self._runtime_config_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_path = (
                self._runtime_config_path.with_suffix(
                    ".tmp"
                )
            )

            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    configuration,
                    file,
                    indent=4,
                )

                file.write("\n")

            temporary_path.replace(
                self._runtime_config_path
            )

        except OSError as error:

            raise ConfigurationError(
                "Unable to save writable application "
                "configuration."
            ) from error

    # =========================================================================
    # Reload
    # =========================================================================

    def reload(self) -> None:
        """
        Reload all configuration.
        """

        self._initialized = False
        self._configs.clear()

        self.initialize(
            self._config_directory or "config"
        )

    # =========================================================================
    # Generic access
    # =========================================================================

    def get(
        self,
        section: str,
    ) -> dict[str, Any]:
        """
        Return a configuration section.
        """

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
        """
        Return a value from a configuration section.
        """

        return self.get(section).get(
            key,
            default,
        )

    # =========================================================================
    # Configuration properties
    # =========================================================================

    @property
    def app(self) -> dict[str, Any]:
        return self.get("app")

    @property
    def providers(self) -> dict[str, Any]:
        return self.get("providers")

    @property
    def models(self) -> dict[str, Any]:
        return self.get("models")

    @property
    def logging(self) -> dict[str, Any]:
        return self.get("logging")

    @property
    def languages(self) -> dict[str, Any]:
        return self.get("languages")

    @property
    def security(self) -> dict[str, Any]:
        return self.get("security")

    @property
    def manifest(self) -> dict[str, Any]:
        return self.get("manifest")

    @property
    def application(self) -> dict[str, Any]:
        return self.get("application")

    # =========================================================================
    # All configuration
    # =========================================================================

    def all(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return every loaded configuration.
        """

        return self._configs.copy()