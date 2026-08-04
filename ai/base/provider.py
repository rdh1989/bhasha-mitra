"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : provider.py
Purpose     : Base interface for all AI providers.

Description:
    Defines the common lifecycle that every AI provider must implement.

    This interface is inherited by:

        • ASR Providers
        • Translation Providers
        • TTS Providers
        • Language Detection Providers
        • Subtitle Providers

Design Pattern:
    Strategy Pattern

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
# from typing import runtime_checkable


# @runtime_checkable
class Provider(ABC):
    """
    Base abstract class for every AI provider.

    Notes
    -----
    • Providers contain inference logic only.
    • Providers must never manage model lifecycle.
    • Model loading/unloading is delegated to ModelManager.
    • Provider implementations should remain lightweight and
      stateless wherever possible.
    """

    __slots__ = ()

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the provider.

        Responsibilities
        ----------------
        • Validate configuration.
        • Initialize provider-specific resources.
        • Request required AI models from ModelManager.

        Raises
        ------
        RuntimeError
            If provider initialization fails.
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify provider health.

        Returns
        -------
        bool
            True if provider is ready for inference.
        """
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown provider gracefully.

        Responsibilities
        ----------------
        • Release provider resources.
        • Notify ModelManager that provider is no longer using
          allocated models.
        """
        raise NotImplementedError