"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Provider Service

Description:
    High-level service responsible for resolving ready-to-use providers.

Design Patterns:
    • Facade
    • Dependency Injection

Responsibilities:
    • Resolve provider classes
    • Create provider instances
    • Initialize providers
    • Return ready providers

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
from ai.core.factory import ProviderFactory
from ai.core.loader import ProviderLoader


class ProviderService:
    """
    High-level service for provider lifecycle management.
    """

    __slots__ = (
        "_factory",
        "_loader",
    )

    def __init__(
        self,
        factory: ProviderFactory,
        loader: ProviderLoader,
    ) -> None:
        self._factory = factory
        self._loader = loader

    def get_provider(
        self,
        category: ProviderCategory,
        provider_name: str,
        **kwargs: Any,
    ) -> Provider:
        """
        Return an initialized provider.
        """

        provider = self._factory.create(
            category=category,
            provider_name=provider_name,
            **kwargs,
        )

        return self._loader.load(provider)

    def shutdown(
        self,
        provider: Provider,
    ) -> None:
        """
        Shutdown a provider.
        """

        self._loader.unload(provider)