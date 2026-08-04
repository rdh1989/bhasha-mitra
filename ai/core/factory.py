"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : factory.py
Purpose     : AI Provider Factory

Description:
    Responsible for creating provider instances using the registered
    provider classes.

Design Patterns:
    • Factory
    • Registry
    • Dependency Injection

Notes:
    • Creates provider instances only.
    • Does NOT initialize providers.
    • Does NOT load AI models.
    • Provider lifecycle is managed by ProviderLoader.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from typing import Any

from ai.base.provider import Provider
from ai.core.constants import ProviderCategory
from ai.core.exceptions import (
    ProviderCreationError,
    ProviderNotFoundError,
)
from ai.core.registry import ProviderRegistry


class ProviderFactory:
    """
    Factory responsible for creating AI provider instances.

    Responsibilities
    ----------------
    • Resolve provider classes from ProviderRegistry.
    • Instantiate provider objects.
    • Support dependency injection through constructor arguments.

    Notes
    -----
    Provider lifecycle (initialize, health check, shutdown)
    is managed by ProviderLoader.
    """

    __slots__ = ("_registry",)

    def __init__(self, registry: ProviderRegistry) -> None:
        """
        Initialize the factory.

        Parameters
        ----------
        registry : ProviderRegistry
            Registry used for provider lookup.
        """
        self._registry = registry

    def create(
        self,
        category: ProviderCategory,
        provider_name: str,
        **kwargs: Any,
    ) -> Provider:
        """
        Create a provider instance.

        Parameters
        ----------
        category : ProviderCategory
            Provider category.

        provider_name : str
            Registered provider name.

        **kwargs
            Constructor dependencies.

        Returns
        -------
        Provider
            Newly created provider instance.

        Raises
        ------
        ProviderNotFoundError
            If the provider is not registered.

        ProviderCreationError
            If instantiation fails.
        """

        try:
            provider_class = self._registry.get(
                category=category,
                provider_name=provider_name,
            )
        except Exception as exc:
            raise ProviderNotFoundError(
                f"Provider '{provider_name}' "
                f"not found in category "
                f"'{category.value}'."
            ) from exc

        try:
            provider = provider_class(**kwargs)
        except Exception as exc:
            raise ProviderCreationError(
                f"Failed to create provider "
                f"'{provider_name}'."
            ) from exc

        if not isinstance(provider, Provider):
            raise ProviderCreationError(
                f"{provider_class.__name__} "
                "does not implement Provider."
            )

        return provider