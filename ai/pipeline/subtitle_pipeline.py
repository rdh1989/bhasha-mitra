"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle_pipeline.py
Purpose     : Video Subtitle Pipeline

Description
-----------
Generates subtitles from a video.

Pipeline
--------
Video
    ↓
Transcript Pipeline
    ↓
Subtitle Service
    ↓
Subtitle File

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from __future__ import annotations

from ai.pipeline.transcript_pipeline import TranscriptPipeline
from ai.subtitle.service import SubtitleService

from ai.pipeline.contracts import (
    VideoSubtitleRequest,
    VideoSubtitleResult,
)


class SubtitlePipeline:
    """
    Subtitle generation pipeline.
    """

    def __init__(
        self,
        transcript_pipeline: TranscriptPipeline,
        subtitle_service: SubtitleService,
    ) -> None:

        self._transcript_pipeline = transcript_pipeline
        self._subtitle_service = subtitle_service

    def execute(
        self,
        request: VideoSubtitleRequest,
    ) -> VideoSubtitleResult:
        """
        Generate subtitles from a video.

        Workflow
        --------
        Video
            ↓
        Transcript Pipeline
            ↓
        Subtitle Service
            ↓
        Subtitle File
        """

        #
        # Future implementation
        #
        # transcript = self._transcript_pipeline.execute(...)
        #
        # subtitle = self._subtitle_service.generate(...)
        #
        # return VideoSubtitleResult(...)
        #

        raise NotImplementedError(
            "Subtitle pipeline is not implemented."
        )