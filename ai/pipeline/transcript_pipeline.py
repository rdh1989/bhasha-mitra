"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : transcript_pipeline.py
Purpose     : Video Transcript Pipeline

Description
-----------
Generates transcript from a video.

Pipeline
--------
Video
    ↓
Audio Extraction
    ↓
Speech Recognition
    ↓
Transcript

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from __future__ import annotations

from ai.asr.service import ASRService

from ai.pipeline.contracts import (
    VideoTranscriptRequest,
    VideoTranscriptResult,
)


class TranscriptPipeline:
    """
    Transcript generation pipeline.
    """

    def __init__(
        self,
        asr_service: ASRService,
    ) -> None:

        self._asr = asr_service

    def execute(
        self,
        request: VideoTranscriptRequest,
    ) -> VideoTranscriptResult:
        """
        Generate transcript from a video.

        Workflow
        --------
        Video
            ↓
        Audio Extraction
            ↓
        Speech Recognition
            ↓
        Transcript
        """

        #
        # TODO
        #
        # Backend utility will extract audio.
        #
        # audio_path = AudioExtractor.extract(
        #     request.video_path
        # )
        #

        raise NotImplementedError(
            "Audio extraction is not implemented."
        )

        #
        # Future
        #
        # asr_result = self._asr.transcribe(audio_path)
        #
        # return VideoTranscriptResult(
        #     transcript=asr_result.transcript,
        #     ...
        # )