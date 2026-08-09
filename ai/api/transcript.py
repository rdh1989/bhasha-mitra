"""
===============================================================================
BHASHA MITRA - AI Framework

Module:
    transcript.py

Layer:
    AI Framework / API

Description:
    AI transcript generation endpoint.

Responsibilities:
    - Validate existing local audio file
    - Invoke framework ASR service
    - Validate ASRResult
    - Persist transcript.json
    - Ensure transcript file is fully written and closed
    - Return transcript metadata
===============================================================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.asr.models import ASRRequest, ASRResult
from ai.core.service_registry import ServiceRegistry


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/transcript",
    tags=["AI Transcript"],
)


# =============================================================================
# Existing ASR Service
# =============================================================================

service = ServiceRegistry.asr_service()


# =============================================================================
# Request
# =============================================================================

class TranscriptRequest(BaseModel):
    """
    Request for transcript generation.
    """

    audio_path: str


# =============================================================================
# Helpers
# =============================================================================

def _serialize_asr_result(
    result: ASRResult,
) -> dict:
    """
    Convert framework-standard ASRResult into a JSON-serializable dictionary.
    """

    return {
        "provider": result.provider,
        "model": result.model,
        "transcript": result.transcript,
        "segments": [
            {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.confidence,
            }
            for segment in result.segments
        ],
        "detected_language": result.detected_language,
        "language_confidence": result.language_confidence,
        "duration_seconds": result.duration_seconds,
        "processing_time_seconds": result.processing_time_seconds,
        "metadata": result.metadata,
        "warnings": result.warnings,
    }


def _persist_transcript(
    audio_path: Path,
    result: ASRResult,
) -> Path:
    """
    Persist the framework transcript artifact next to the audio file.

    The file is explicitly opened using a context manager so that it is
    completely flushed and CLOSED before this function returns.

    This is important on Windows because the preprocessing worker may
    immediately access the generated transcript.json.
    """

    transcript_path = (
        audio_path.parent / "transcript.json"
    )

    transcript_data = _serialize_asr_result(
        result
    )

    logger.info(
        "TRANSCRIPT FILE WRITE STARTED | path=%s",
        transcript_path,
    )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # Use an explicit file handle and context manager.
    #
    # The file is guaranteed to be closed when the block exits.
    # -------------------------------------------------------------------------

    with transcript_path.open(
        "w",
        encoding="utf-8",
    ) as transcript_file:

        json.dump(
            transcript_data,
            transcript_file,
            ensure_ascii=False,
            indent=2,
        )

        transcript_file.flush()

    # -------------------------------------------------------------------------
    # File handle is CLOSED here.
    # -------------------------------------------------------------------------

    logger.info(
        "TRANSCRIPT FILE WRITE COMPLETED | "
        "path=%s | closed=True",
        transcript_path,
    )

    # -------------------------------------------------------------------------
    # Verify the file exists and can be opened for reading.
    # -------------------------------------------------------------------------

    if not transcript_path.is_file():

        raise RuntimeError(
            "Transcript file was not created."
        )

    # -------------------------------------------------------------------------
    # Verify that the file can actually be opened after writing.
    #
    # This also confirms that the current process is no longer holding
    # an exclusive write handle.
    # -------------------------------------------------------------------------

    try:

        with transcript_path.open(
            "r",
            encoding="utf-8",
        ) as transcript_file:

            json.load(
                transcript_file
            )

    except Exception as exc:

        logger.exception(
            "TRANSCRIPT FILE VALIDATION FAILED | "
            "path=%s | error_type=%s | error=%s",
            transcript_path,
            type(exc).__name__,
            exc,
        )

        raise RuntimeError(
            "Generated transcript file could not be validated."
        ) from exc

    logger.info(
        "TRANSCRIPT FILE READY FOR CONSUMER | "
        "path=%s | size=%d bytes | closed=True",
        transcript_path,
        transcript_path.stat().st_size,
    )

    return transcript_path


# =============================================================================
# Transcript API
# =============================================================================

@router.post("")
def generate_transcript(
    request: TranscriptRequest,
) -> dict:
    """
    Generate transcript from an existing local audio file.
    """

    logger.info(
        "TRANSCRIPT REQUEST RECEIVED | audio=%s",
        request.audio_path,
    )

    # =========================================================================
    # Validate audio
    # =========================================================================

    audio_path = (
        Path(request.audio_path)
        .expanduser()
        .resolve()
    )

    logger.info(
        "TRANSCRIPT AUDIO PATH RESOLVED | path=%s",
        audio_path,
    )

    if not audio_path.exists():

        logger.error(
            "TRANSCRIPT AUDIO FILE NOT FOUND | path=%s",
            audio_path,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Audio file does not exist: "
                f"{audio_path}"
            ),
        )

    if not audio_path.is_file():

        logger.error(
            "TRANSCRIPT AUDIO PATH IS NOT A FILE | path=%s",
            audio_path,
        )

        raise HTTPException(
            status_code=400,
            detail="Audio path is not a file.",
        )

    logger.info(
        "TRANSCRIPT AUDIO VALIDATED | "
        "path=%s | size=%d bytes",
        audio_path,
        audio_path.stat().st_size,
    )

    # =========================================================================
    # Create ASR request
    # =========================================================================

    try:

        asr_request = ASRRequest(
            audio_path=str(audio_path),
        )

        logger.info(
            "ASR REQUEST CREATED | audio=%s",
            audio_path,
        )

    except Exception as exc:

        logger.exception(
            "ASR REQUEST CREATION FAILED | "
            "audio=%s | error_type=%s | error=%s",
            audio_path,
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid ASR request: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    # =========================================================================
    # ASR
    # =========================================================================

    try:

        logger.warning(
            "ASR SERVICE CALL STARTED | "
            "audio=%s | service=%s",
            audio_path,
            type(service).__name__,
        )

        result = service.transcribe(
            asr_request
        )

        logger.warning(
            "ASR SERVICE CALL RETURNED | "
            "audio=%s | result_type=%s",
            audio_path,
            type(result).__name__,
        )

        # =====================================================================
        # Validate ASR result
        # =====================================================================

        if not isinstance(
            result,
            ASRResult,
        ):

            logger.error(
                "ASR SERVICE RETURNED INVALID RESULT | "
                "audio=%s | result_type=%s",
                audio_path,
                type(result).__name__,
            )

            raise RuntimeError(
                "ASR service returned an invalid ASRResult."
            )

        logger.info(
            "ASR RESULT VALIDATED | "
            "audio=%s | provider=%s | model=%s | "
            "language=%s | segments=%d",
            audio_path,
            result.provider,
            result.model,
            result.detected_language,
            len(result.segments),
        )

        # =====================================================================
        # Persist transcript
        # =====================================================================

        transcript_path = _persist_transcript(
            audio_path,
            result,
        )

        logger.info(
            "TRANSCRIPT ARTIFACT READY | "
            "audio=%s | transcript=%s",
            audio_path,
            transcript_path,
        )

        # =====================================================================
        # Response
        # =====================================================================

        response = {
            "status": "PASS",
            "transcript_path": str(
                transcript_path
            ),
            "provider": result.provider,
            "model": result.model,
            "transcript": result.transcript,
            "detected_language": (
                result.detected_language
            ),
            "language_confidence": (
                result.language_confidence
            ),
            "duration_seconds": (
                result.duration_seconds
            ),
            "processing_time_seconds": (
                result.processing_time_seconds
            ),
            "segment_count": len(
                result.segments
            ),
            "warnings": result.warnings,
        }

        logger.warning(
            "TRANSCRIPT GENERATION COMPLETED | "
            "audio=%s | transcript=%s | "
            "file_ready=True",
            audio_path,
            transcript_path,
        )

        return response

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "TRANSCRIPT / ASR FAILED | "
            "audio=%s | error_type=%s | error=%s",
            audio_path,
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Transcript generation failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc