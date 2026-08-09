"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Subtitle Generation Service

Description:
    Generates subtitle files using a configured subtitle format.

    SubtitleService contains no format-specific implementation.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.subtitle.adapter import SubtitleAdapter
from pathlib import Path
import math

from ai.subtitle.config import SubtitleConfig
from ai.subtitle.format_registry import (
    SubtitleFormatRegistry,
)
from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)


class SubtitleService:
    """
    Subtitle orchestration service.

    Responsibilities
    ----------------
    • Validate subtitle requests.
    • Resolve configured subtitle format.
    • Delegate generation to the configured formatter.
    • Normalize the result.

    The service contains NO format-specific logic.
    """

    def __init__(
        self,
        adapter: SubtitleAdapter,
        config: SubtitleConfig | None = None,
    ) -> None:

        self._adapter = adapter

        self._config = config or SubtitleConfig.from_yaml(
            Path(__file__).resolve().parents[2] / "config" / "providers.yaml"
        )

        self._format_registry = (
            SubtitleFormatRegistry(
                self._config
            )
        )

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitle using the configured format.
        """

        if not request.segments:
            raise ValueError(
                "Subtitle segments cannot be empty."
            )

        for segment in request.segments:
            if (
                not math.isfinite(segment.start)
                or not math.isfinite(segment.end)
                or segment.start < 0
                or segment.end < segment.start
            ):
                raise ValueError(
                    "Subtitle segment timestamps must be finite, non-negative, "
                    "and end no earlier than start."
                )

            if not segment.text.strip():
                raise ValueError("Subtitle segment text cannot be empty.")

        subtitle_format = (
            request.subtitle_format
            or self._config.default_format
        ).strip().lower()

        formatter = (
            self._format_registry.get(
                subtitle_format
            )
        )

        provider_result = formatter.generate(
            request
        )

        return self._adapter.to_framework_result(
            provider_result
        )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(
        self,
    ) -> bool:
        """
        Verify subtitle format configuration.
        """

        try:

            self._format_registry.get(
                self._config.default_format
            )

            return True

        except Exception:

            return False
