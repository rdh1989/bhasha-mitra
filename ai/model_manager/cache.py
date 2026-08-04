"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : cache.py
Purpose     : AI Model Cache

Description:
    Maintains loaded AI model instances in memory.

Design Pattern:
    Cache

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from typing import Any


class ModelCache:
    """
    In-memory cache for loaded AI models.

    Responsibilities
    ----------------
    • Store loaded model instances
    • Retrieve cached models
    • Remove cached models
    • Clear cache

    Notes
    -----
    This class does NOT:
        • Load models
        • Validate models
        • Read manifests
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def add(
        self,
        model_name: str,
        model: Any,
    ) -> None:
        """
        Add a model to cache.

        Parameters
        ----------
        model_name : str
            Unique model identifier.

        model : Any
            Loaded model instance.
        """

        self._cache[model_name] = model

    def get(
        self,
        model_name: str,
    ) -> Any:
        """
        Retrieve cached model.

        Parameters
        ----------
        model_name : str

        Returns
        -------
        Any

        Raises
        ------
        KeyError
            Model not found in cache.
        """

        return self._cache[model_name]

    def exists(
        self,
        model_name: str,
    ) -> bool:
        """
        Check whether a model is cached.

        Parameters
        ----------
        model_name : str

        Returns
        -------
        bool
        """

        return model_name in self._cache

    def remove(
        self,
        model_name: str,
    ) -> None:
        """
        Remove a cached model.

        Parameters
        ----------
        model_name : str
        """

        self._cache.pop(model_name, None)

    def clear(self) -> None:
        """
        Remove all cached models.
        """

        self._cache.clear()

    def size(self) -> int:
        """
        Return number of cached models.

        Returns
        -------
        int
        """

        return len(self._cache)

    def list(self) -> list[str]:
        """
        Return cached model names.

        Returns
        -------
        list[str]
        """

        return sorted(self._cache.keys())