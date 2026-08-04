"""
Configuration Repository Contract.

Responsible for reading and persisting application configuration.

The Application layer depends only on this abstraction and never
accesses YAML, JSON, or other configuration formats directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConfigRepository(ABC):
    """
    Repository for application configuration.
    """

    # ==========================================================
    # Generic Operations
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
            get("storage.uploads")
            get("models.whisper")
        """

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Update a configuration value.
        """

    @abstractmethod
    def has(
        self,
        key: str,
    ) -> bool:
        """
        Returns True if the key exists.
        """

    @abstractmethod
    def remove(
        self,
        key: str,
    ) -> None:
        """
        Remove a configuration value.
        """

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    def load(self) -> None:
        """
        Load configuration from the persistence source.
        """

    @abstractmethod
    def reload(self) -> None:
        """
        Reload configuration from the persistence source.
        """

    @abstractmethod
    def save(self) -> None:
        """
        Persist configuration changes.
        """

    # ==========================================================
    # Export
    # ==========================================================

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """
        Return the complete configuration.
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all loaded configuration values.
        """