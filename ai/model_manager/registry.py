"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : registry.py
Purpose     : AI Model Registry

Description:
    Stores metadata about all AI models known to the framework.

Design Pattern:
    Registry Pattern

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.core.exceptions import ModelNotFoundError


class ModelRegistry:
    """
    Registry containing metadata for all available AI models.

    Notes
    -----
    This registry stores model metadata only.

    It does NOT

    • Load models
    • Cache models
    • Perform inference
    """

    def __init__(self) -> None:
        self._models: dict[str, dict[str, Any]] = {}

    @staticmethod
    def build_key(
        category: str,
        model: str,
    ) -> str:
        """
        Build unique registry key.
        """

        return f"{category}:{model}"

    def register(
        self,
        category: str,
        model: str,
        model_path: Path,
        provider: str,
        version: str,
    ) -> None:
        """
        Register model metadata.
        """

        key = self.build_key(category, model)

        self._models[key] = {
            "category": category,
            "model": model,
            "path": model_path,
            "provider": provider,
            "version": version,
        }

    def unregister(
        self,
        category: str,
        model: str,
    ) -> None:
        """
        Remove model registration.
        """

        key = self.build_key(category, model)
        self._models.pop(key, None)

    def exists(
        self,
        category: str,
        model: str,
    ) -> bool:
        """
        Check whether model is registered.
        """

        key = self.build_key(category, model)
        return key in self._models

    def get(
        self,
        category: str,
        model: str,
    ) -> dict[str, Any]:
        """
        Return model metadata.
        """

        key = self.build_key(category, model)

        if key not in self._models:
            raise ModelNotFoundError(
                f"Model '{key}' is not registered."
            )

        return self._models[key]

    def list(self) -> list[str]:
        """
        Return registered model keys.
        """

        return sorted(self._models.keys())

    def clear(self) -> None:
        """
        Remove every registered model.
        """

        self._models.clear()

    def size(self) -> int:
        """
        Return total registered models.
        """

        return len(self._models)