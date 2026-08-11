"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : voice_cloning.py
Purpose     : Voice Cloning API
===============================================================================
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.voice_cloning.models import VoiceDubbingRequest


router = APIRouter()

logger = logging.getLogger(__name__)


class VoiceCloningRequest(BaseModel):
    audio_path: str = Field(..., description="Path to source audio.wav")
    translation_path: str = Field(..., description="Path to translation.json")
    transcript_path: str | None = Field(
        None,
        description="Optional path to transcript.json",
    )
    output_path: str | None = Field(
        None,
        description="Optional output dubbed wav path",
    )
    language: str = Field("mr", description="Target language")
    model_path: str | None = Field(
        None,
        description="Optional IndicF5 model path; defaults to VOICE_CLONING_MODEL_PATH env var",
    )


@router.post(
    "/voice-cloning",
    summary="Generate Voice-Cloned Dubbed Audio",
)
def voice_cloning(
    request: VoiceCloningRequest,
) -> dict:

    model_path = request.model_path or os.getenv(
        "VOICE_CLONING_MODEL_PATH"
    )

    if not model_path:
        raise HTTPException(
            status_code=400,
            detail=(
                "Voice cloning model path is missing. Provide model_path "
                "in request body or set VOICE_CLONING_MODEL_PATH."
            ),
        )

    try:

        from ai.voice_cloning.service import (
            VoiceDubbingService,
        )

        service = VoiceDubbingService(
            model_path=Path(model_path),
        )

        result = service.dub(
            VoiceDubbingRequest(
                audio_path=Path(request.audio_path),
                translation_path=Path(request.translation_path),
                transcript_path=(
                    Path(request.transcript_path)
                    if request.transcript_path
                    else None
                ),
                output_path=(
                    Path(request.output_path)
                    if request.output_path
                    else None
                ),
                language=request.language,
            )
        )

        logger.info(
            "VOICE CLONING COMPLETED | audio=%s | segments=%s",
            result.audio_path,
            result.segments_generated,
        )

        return {
            "audio_path": str(result.audio_path),
            "language": result.language,
            "sample_rate": result.sample_rate,
            "duration": result.duration,
            "segments_generated": result.segments_generated,
        }

    except ValueError as exc:

        logger.warning(
            "VOICE CLONING VALIDATION FAILED | error=%s",
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except FileNotFoundError as exc:

        logger.warning(
            "VOICE CLONING INPUT MISSING | error=%s",
            exc,
        )

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ModuleNotFoundError as exc:

        logger.exception(
            "VOICE CLONING DEPENDENCY MISSING | error=%s",
            exc,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Voice cloning dependencies are missing in the current "
                "environment. Install required packages (numpy, soundfile, "
                "transformers) and retry."
            ),
        )

    except Exception as exc:

        logger.exception(
            "VOICE CLONING FAILED | error=%s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
