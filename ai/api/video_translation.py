"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : video_translation.py
Purpose     : Video Translation API

Description
-----------
REST endpoints for complete AI video translation.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.pipeline.contracts import (
    VideoTranslationRequest,
)

from ai.core.pipeline_registry import PipelineRegistry


router = APIRouter()


# -------------------------------------------------------------------------
# Pipeline
# -------------------------------------------------------------------------

pipeline = PipelineRegistry.video_translation_pipeline()


# -------------------------------------------------------------------------
# AI-010
# -------------------------------------------------------------------------

@router.post(
    "/video/translate",
    summary="Translate Video",
)
def translate_video(
    request: VideoTranslationRequest,
):
    """
    Execute complete video translation pipeline.
    """

    try:

        result = pipeline.execute(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )