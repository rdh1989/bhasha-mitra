"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : service.py
Purpose     : Subtitle Generation Service

Description:
    Generates subtitle files from transcription results.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)


class SubtitleService:
    """
    Subtitle orchestration service.

    Responsibilities
    ----------------
    • Generate subtitle files.
    • Return framework models.

    Notes
    -----
    Subtitle generation does not require an AI model.
    It simply converts an ASRResult into a subtitle file.
    """

    def __init__(self) -> None:
        pass

    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitle file.
        """

        #
        # TODO
        # Move the working subtitle generation
        # implementation here.
        #

        raise NotImplementedError(
            "Move subtitle generation implementation here."
        )

    def health_check(self) -> bool:
        """
        Subtitle service is always available.
        """

        return True