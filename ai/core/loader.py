"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : loader.py
Purpose     : Provider Loader

Description:
    Responsible for initializing and validating AI providers.

Design Patterns:
    • Dependency Injection

Responsibilities:
    • Initialize providers
    • Verify provider health
    • Shutdown providers

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.base.provider import Provider
from ai.core.exceptions import (
    ProviderHealthError,
    ProviderInitializationError,
)


class ProviderLoader:
    """
    Manages the lifecycle of AI providers.

    Notes
    -----
    • Does not create providers.
    • Does not register providers.
    • Does not load AI models directly.
    """

    __slots__ = ()

    def load(
        self,
        provider: Provider,
    ) -> Provider:
        """
        Initialize and validate a provider.

        Parameters
        ----------
        provider : Provider

        Returns
        -------
        Provider
            Ready-to-use provider.

        Raises
        ------
        ProviderInitializationError
        ProviderHealthError
        """

        try:
            provider.initialize()

        except Exception as exc:
            raise ProviderInitializationError(
                "Provider initialization failed."
            ) from exc

        try:

            if not provider.health_check():

                raise ProviderHealthError(
                    "Provider health check failed."
                )

        except ProviderHealthError:
            raise

        except Exception as exc:

            raise ProviderHealthError(
                "Provider health check failed."
            ) from exc

        return provider

    def unload(
        self,
        provider: Provider,
    ) -> None:
        """
        Shutdown provider gracefully.
        """

        provider.shutdown()