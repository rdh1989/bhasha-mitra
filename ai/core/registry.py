"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : registry.py
Purpose     : AI Provider Registry

Description:
    Central registry responsible for maintaining mappings between
    provider names and their implementation classes.

    The registry enables provider discovery without coupling the
    framework to any specific AI implementation.

Design Patterns:
    • Registry
    • Strategy

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from typing import Type

from ai.base.provider import Provider
from ai.core.exceptions import ProviderRegistrationError


class ProviderRegistry:
    """
    Central registry for AI providers.

    Notes
    -----
    • Stores provider implementations by category.
    • Used by ProviderFactory.
    • Does not instantiate providers.
    """

    __slots__ = ("_providers",)

    def __init__(self) -> None:
        """
        Initialize an empty provider registry.
        """

        self._providers: dict[str, dict[str, Type[Provider]]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        category: str,
        provider_name: str,
        provider_class: Type[Provider],
    ) -> None:
        """
        Register a provider implementation.

        Parameters
        ----------
        category : str
            Provider category (asr, translation, tts, etc.).

        provider_name : str
            Unique provider name.

        provider_class : Type[Provider]
            Provider implementation class.
        """

        category = category.lower()
        provider_name = provider_name.lower()

        self._providers.setdefault(category, {})

        if provider_name in self._providers[category]:
            raise ProviderRegistrationError(
                f"Provider '{provider_name}' "
                f"is already registered "
                f"for category '{category}'."
            )

        self._providers[category][provider_name] = provider_class

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        category: str,
        provider_name: str,
    ) -> Type[Provider]:
        """
        Retrieve a registered provider class.

        Raises
        ------
        ProviderRegistrationError
            If provider is not registered.
        """

        category = category.lower()
        provider_name = provider_name.lower()

        try:
            return self._providers[category][provider_name]
        except KeyError as exc:
            raise ProviderRegistrationError(
                f"Unknown provider '{provider_name}' "
                f"for category '{category}'."
            ) from exc

    def exists(
        self,
        category: str,
        provider_name: str,
    ) -> bool:
        """
        Check whether a provider is registered.
        """

        category = category.lower()
        provider_name = provider_name.lower()

        return (
            category in self._providers
            and provider_name in self._providers[category]
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def providers(
        self,
        category: str,
    ) -> list[str]:
        """
        Return all registered providers for a category.
        """

        return sorted(
            self._providers.get(category.lower(), {}).keys()
        )

    def categories(self) -> list[str]:
        """
        Return all registered provider categories.
        """

        return sorted(self._providers.keys())

    def clear(self) -> None:
        """
        Remove all registered providers.

        Primarily intended for unit testing.
        """

        self._providers.clear()