"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Package     : pipeline
Purpose     : AI Workflow Pipelines

Description
-----------
Contains orchestration pipelines that combine multiple AI services
to accomplish higher-level business workflows.

Pipelines
---------
• VideoTranslationPipeline
• TranscriptPipeline
• SubtitlePipeline
• DubbingPipeline

Notes
-----
A pipeline never performs AI inference directly.

It orchestrates existing AI services.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from ai.pipeline.video_translation_pipeline import VideoTranslationPipeline
from ai.pipeline.transcript_pipeline import TranscriptPipeline
from ai.pipeline.subtitle_pipeline import SubtitlePipeline
from ai.pipeline.dubbing_pipeline import DubbingPipeline

__all__ = [
    "VideoTranslationPipeline",
    "TranscriptPipeline",
    "SubtitlePipeline",
    "DubbingPipeline",
]