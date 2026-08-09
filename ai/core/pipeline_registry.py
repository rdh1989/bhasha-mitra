"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : pipeline_registry.py
Purpose     : AI Pipeline Registry

Description
-----------
Constructs AI pipelines with their required dependencies.

Responsibilities
----------------
• Create pipeline instances
• Resolve service dependencies
• Hide pipeline construction from API layer

Notes
-----
Pipelines are orchestrators.
AI services are obtained from ServiceRegistry.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.core.service_registry import ServiceRegistry

from ai.pipeline.transcript_pipeline import (
    TranscriptPipeline,
)

from ai.pipeline.subtitle_pipeline import (
    SubtitlePipeline,
)

from ai.pipeline.dubbing_pipeline import (
    DubbingPipeline,
)

from ai.pipeline.video_translation_pipeline import (
    VideoTranslationPipeline,
)

from ai.pipeline.tts_pipeline import TTSPipeline

class PipelineRegistry:
    """
    Creates AI pipeline instances.
    """

    # -------------------------------------------------------------------------
    # Transcript Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def transcript_pipeline() -> TranscriptPipeline:
        """
        Create Transcript Pipeline.

        Flow
        ----
        Audio
            ↓
        ASR
            ↓
        Translation
            ↓
        Translated Text
        """

        return TranscriptPipeline()

    # -------------------------------------------------------------------------
    # Subtitle Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def subtitle_pipeline() -> SubtitlePipeline:
        """
        Create Subtitle Pipeline.
        """

        return SubtitlePipeline(
            transcript_pipeline=(
                PipelineRegistry.transcript_pipeline()
            ),
            subtitle_service=(
                ServiceRegistry.subtitle_service()
            ),
        )

    # -------------------------------------------------------------------------
    # Dubbing Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def dubbing_pipeline() -> DubbingPipeline:

        return DubbingPipeline(
            tts_service=(
                ServiceRegistry.tts_service()
            ),
        )

    # -------------------------------------------------------------------------
    # Video Translation Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def video_translation_pipeline() -> VideoTranslationPipeline:
        """
        Create Video Translation Pipeline.

        This pipeline orchestrates the AI-side workflow.
        """

        return VideoTranslationPipeline(
            transcript_pipeline=(
                PipelineRegistry.transcript_pipeline()
            ),
            subtitle_pipeline=(
                PipelineRegistry.subtitle_pipeline()
            ),
            dubbing_pipeline=(
                PipelineRegistry.dubbing_pipeline()
            ),
            language_service=(
                ServiceRegistry.language_detection_service()
            ),
            translation_service=(
                ServiceRegistry.translation_service()
            ),
        )

    # -------------------------------------------------------------------------
    # TTS Pipeline
    # -------------------------------------------------------------------------

    @staticmethod
    def tts_pipeline() -> TTSPipeline:
        """
        Create TTS Pipeline.
        """

        return TTSPipeline()