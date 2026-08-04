"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Subtitle Generation Service

Description:
    Generates subtitle files from transcription results.

Design Pattern:
    • Strategy
    • Dependency Injection

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from app.ai.base.subtitle_provider import SubtitleProvider
from app.ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)


class SubtitleService:
    """
    Subtitle orchestration service.

    Responsibilities
    ----------------
    • Generate subtitle files.
    • Delegate subtitle generation to the configured provider.
    • Return framework models.
    """

    def __init__(
        self,
        provider: SubtitleProvider,
    ) -> None:
        self._provider = provider

    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitle file.

        Parameters
        ----------
        request : SubtitleRequest

        Returns
        -------
        SubtitleResult
        """

        return self._provider.generate(
            transcription=request.transcription,
            output_path=request.output_path,
            subtitle_format=request.subtitle_format,
        )

    def health_check(self) -> bool:
        """
        Verify provider health.
        """

        return self._provider.health_check()