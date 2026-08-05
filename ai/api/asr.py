"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : asr.py
Purpose     : Speech Recognition API

Description
-----------
REST endpoints for Automatic Speech Recognition (ASR).

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.asr.models import (
    ASRRequest,
)

from ai.core.service_registry import ServiceRegistry

router = APIRouter()


# -------------------------------------------------------------------------
# Service
# -------------------------------------------------------------------------

service = ServiceRegistry.asr_service()


# -------------------------------------------------------------------------
# AI-005
# -------------------------------------------------------------------------

@router.post(
    "/asr",
    summary="Speech Recognition",
)
def speech_to_text(
    request: ASRRequest,
):
    """
    Convert speech into text.
    """

    try:

        return service.transcribe(request)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )