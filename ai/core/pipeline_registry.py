"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : pipeline_registry.py
Purpose     : AI Pipeline Registry

Description
-----------
Constructs AI pipelines with all required dependencies.

Responsibilities
----------------
• Create pipeline instances
• Resolve service dependencies
• Hide pipeline construction from API layer

Notes
-----
Pipelines are orchestrators.
Services are obtained from ServiceRegistry.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.core.service_registry import ServiceRegistry

from ai.pipeline.transcript_pipeline import TranscriptPipeline
from ai.pipeline.subtitle_pipeline import SubtitlePipeline
from ai.pipeline.dubbing_pipeline import DubbingPipeline
from ai.pipeline.video_translation_pipeline import (
    VideoTranslationPipeline,
)


class PipelineRegistry:
    """
    Creates AI pipeline instances.
    """

    # -------------------------------------------------------------------------
    # Transcript Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def transcript_pipeline() -> TranscriptPipeline:

        return TranscriptPipeline(
            asr_service=ServiceRegistry.asr_service(),
        )

    # -------------------------------------------------------------------------
    # Subtitle Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def subtitle_pipeline() -> SubtitlePipeline:

        return SubtitlePipeline(
            transcript_pipeline=PipelineRegistry.transcript_pipeline(),
            subtitle_service=ServiceRegistry.subtitle_service(),
        )

    # -------------------------------------------------------------------------
    # Dubbing Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def dubbing_pipeline() -> DubbingPipeline:

        return DubbingPipeline(
            transcript_pipeline=PipelineRegistry.transcript_pipeline(),
            translation_service=ServiceRegistry.translation_service(),
            tts_service=ServiceRegistry.tts_service(),
        )

    # -------------------------------------------------------------------------
    # Video Translation Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def video_translation_pipeline() -> VideoTranslationPipeline:

        return VideoTranslationPipeline(
            transcript_pipeline=PipelineRegistry.transcript_pipeline(),
            subtitle_pipeline=PipelineRegistry.subtitle_pipeline(),
            dubbing_pipeline=PipelineRegistry.dubbing_pipeline(),
            language_service=ServiceRegistry.language_detection_service(),
            translation_service=ServiceRegistry.translation_service(),
        )