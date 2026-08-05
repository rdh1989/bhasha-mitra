"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : tts.py
Purpose     : Text-to-Speech API

Description
-----------
REST endpoints for Text-to-Speech.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.core.service_registry import ServiceRegistry

from ai.tts.models import (
    SpeechRequest,
    SpeechResult,
)

router = APIRouter()


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

service = ServiceRegistry.tts_service()


# --------------------------------------------------------------------------
# AI-008
# --------------------------------------------------------------------------

@router.post(
    "/tts",
    summary="Text To Speech",
)

def text_to_speech(
    request: SpeechRequest,
):
    """
    Convert text into speech.
    """

    try:

        result = service.synthesize(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )