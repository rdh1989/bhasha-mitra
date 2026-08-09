"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : dubbing.py
Purpose     : AI Dubbing API

Description:
    Generates dubbed audio from translated text.

    The API delegates all dubbing processing to DubbingPipeline.
    Long-text handling is performed internally by the pipeline.

Flow
----
Translated Text
    ↓
Dubbing API
    ↓
DubbingPipeline
    ↓
TTSService
    ↓
Dubbed Audio

Author:
    Bhasha Mitra AI Team

Version:
    1.1
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.core.pipeline_registry import PipelineRegistry

from ai.pipeline.contracts import (
    VideoDubbingRequest,
)

router = APIRouter()


# =============================================================================
# Pipeline
# =============================================================================

pipeline = PipelineRegistry.dubbing_pipeline()


# =============================================================================
# AI Dubbing
# =============================================================================

@router.post(
    "/dubbing",
    summary="Generate Dubbed Audio",
)
def generate_dubbing(
    request: VideoDubbingRequest,
):
    """
    Generate dubbed audio from translated text.

    Long translated text is handled internally by DubbingPipeline.
    The API layer does not perform text chunking or TTS processing.
    """

    try:

        return pipeline.execute(
            request
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )