"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : language_detection.py
Purpose     : Language Detection API

Description
-----------
REST endpoints for language detection.

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
from ai.language_detection.models import (
    LanguageDetectionRequest,
    LanguageDetectionResult,
)

router = APIRouter()

# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

service = ServiceRegistry.language_detection_service()

# --------------------------------------------------------------------------
# AI-007
# --------------------------------------------------------------------------

@router.post(
    "/language-detection",
    response_model=LanguageDetectionResult,
    summary="Detect Language",
)
def detect_language(
    request: LanguageDetectionRequest,
):
    """
    Detect input language.
    """

    try:

        result = service.detect(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )