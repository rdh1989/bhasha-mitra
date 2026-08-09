"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : format_registry.py
Purpose     : Subtitle Format Registry

Description:
    Resolves subtitle format implementations from configuration.

    SubtitleService does not know about SRT, VTT, ASS, WebVTT, or any other
    concrete format.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

import importlib
from typing import Protocol

from ai.subtitle.config import (
    SubtitleConfig,
    SubtitleFormatConfig,
)
from ai.subtitle.models import SubtitleRequest, SubtitleResult


class SubtitleFormatter(Protocol):
    """Contract implemented by every configured subtitle formatter."""

    def generate(self, request: SubtitleRequest) -> SubtitleResult:
        """Generate a subtitle file for *request*."""


class SubtitleFormatRegistry:
    """
    Resolves configured subtitle format implementations.
    """

    def __init__(
        self,
        config: SubtitleConfig,
    ) -> None:

        self._config = config

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------

    def get(
        self,
        subtitle_format: str,
    ) -> SubtitleFormatter:
        """
        Resolve the configured formatter for a subtitle format.
        """

        format_name = (
            subtitle_format.strip().lower()
        )

        format_config = self._config.formats.get(
            format_name
        )

        if format_config is None:
            raise ValueError(
                f"Subtitle format '{format_name}' "
                "is not configured."
            )

        if not format_config.enabled:
            raise ValueError(
                f"Subtitle format '{format_name}' "
                "is disabled."
            )

        if not format_config.implementation:
            raise ValueError(
                f"No implementation configured for "
                f"subtitle format '{format_name}'."
            )

        return self._load_implementation(
            format_config
        )

    # ------------------------------------------------------------------
    # Implementation loader
    # ------------------------------------------------------------------

    def _load_implementation(
        self,
        config: SubtitleFormatConfig,
    ) -> SubtitleFormatter:
        """
        Dynamically load configured formatter.

        Expected format:

            package.module:ClassName

        The class constructor receives the loaded ``SubtitleConfig``.
        """

        try:
            module_name, class_name = config.implementation.split(":", 1)
        except ValueError as exc:
            raise ValueError(
                "Subtitle implementation must use 'package.module:ClassName'."
            ) from exc

        if not module_name or not class_name:
            raise ValueError(
                "Subtitle implementation must use 'package.module:ClassName'."
            )

        module = importlib.import_module(
            module_name
        )

        implementation = getattr(
            module,
            class_name,
        )

        formatter = implementation(self._config)
        if not callable(getattr(formatter, "generate", None)):
            raise TypeError(
                f"Subtitle implementation '{config.implementation}' "
                "must define generate(request)."
            )

        return formatter
