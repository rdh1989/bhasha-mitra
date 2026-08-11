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

import logging

from fastapi import APIRouter, HTTPException

from ai.core.pipeline_registry import PipelineRegistry

from ai.pipeline.contracts import (
    VideoDubbingRequest,
)

router = APIRouter()

logger = logging.getLogger(__name__)


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

        logger.info(
            "AI DUBBING REQUEST RECEIVED | "
            "translation=%s | "
            "language=%s | "
            "voice=%s | "
            "output=%s",
            request.translated_text_path,
            request.language,
            request.voice,
            request.output_path,
        )

        result = pipeline.execute(
            request
        )

        logger.info(
            "AI DUBBING REQUEST COMPLETED | "
            "translation=%s | "
            "output=%s",
            request.translated_text_path,
            request.output_path,
        )

        return result

    except ValueError as exc:

        logger.warning(
            "AI DUBBING VALIDATION FAILED | "
            "translation=%s | "
            "error=%s",
            request.translated_text_path,
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except FileNotFoundError as exc:

        logger.warning(
            "AI DUBBING INPUT MISSING | "
            "translation=%s | "
            "error=%s",
            request.translated_text_path,
            exc,
        )

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except RuntimeError as exc:

        logger.exception(
            "AI DUBBING RUNTIME FAILURE | "
            "translation=%s | "
            "error=%s",
            request.translated_text_path,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "AI DUBBING UNEXPECTED FAILURE | "
            "translation=%s | "
            "error=%s",
            request.translated_text_path,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )