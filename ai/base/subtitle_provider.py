"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle_provider.py
Purpose     : Base interface for all Subtitle providers

Description:
    Defines the provider-independent contract that every Subtitle provider
    must implement.

Examples:
    • SRT
    • WebVTT
    • ASS/SSA
    • Future subtitle providers

Design Pattern:
    Strategy Pattern

Author:
    Bhasha Mitra AI Team
===============================================================================
"""

from __future__ import annotations

from abc import abstractmethod

from ai.base.provider import Provider

from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)


class SubtitleProvider(Provider):
    """
    Base interface for all Subtitle providers.

    Providers receive framework-level SubtitleRequest objects and return
    framework-level SubtitleResult objects.

    Provider-specific implementation details must remain inside the
    concrete provider.
    """

    __slots__ = ()

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    @abstractmethod
    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitles.

        Parameters
        ----------
        request : SubtitleRequest
            Provider-independent subtitle generation request.

        Returns
        -------
        SubtitleResult
            Provider-independent subtitle generation result.
        """

        raise NotImplementedError

    # ------------------------------------------------------------------
    # Supported Formats
    # ------------------------------------------------------------------

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """
        Return subtitle formats supported by the provider.

        Returns
        -------
        list[str]
            Supported subtitle formats.
        """

        raise NotImplementedError