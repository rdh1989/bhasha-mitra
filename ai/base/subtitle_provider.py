"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle_provider.py
Purpose     : Base interface for all Subtitle providers.

Description:
    Defines the contract that every Subtitle provider must implement.

    Examples:
        • SRT Generator
        • WebVTT Generator
        • ASS Generator
        • Custom Subtitle Providers

Design Pattern:
    Strategy Pattern

Author:
    Bhasha Mitra AI Team

Version:
    1.0
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

    Notes
    -----
    • Generates subtitle files.
    • Does not manage model lifecycle.
    • Returns framework models only.
    """

    __slots__ = ()

    @abstractmethod
    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitle file.

        Parameters
        ----------
        request : SubtitleRequest
            Subtitle generation request.

        Returns
        -------
        SubtitleResult
            Provider-independent subtitle generation result.
        """
        raise NotImplementedError

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """
        Return supported subtitle formats.

        Returns
        -------
        list[str]
        """
        raise NotImplementedError