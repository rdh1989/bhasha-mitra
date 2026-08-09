"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : tts.py
Purpose     : Text-to-Speech API
===============================================================================
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai.core.pipeline_registry import PipelineRegistry
from ai.tts.models import SpeechRequest


router = APIRouter()

pipeline = PipelineRegistry.tts_pipeline()


@router.post(
    "/tts",
    summary="Convert Text to Speech",
)
def synthesize(
    request: SpeechRequest,
):
    """
    Convert text into speech.
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

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )