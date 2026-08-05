"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle.py
Purpose     : Subtitle Generation API

Description
-----------
REST endpoints for subtitle generation.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.subtitle.service import SubtitleService
from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)

router = APIRouter()


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

service = SubtitleService()


# --------------------------------------------------------------------------
# AI-009
# --------------------------------------------------------------------------

@router.post(
    "/subtitles",
    response_model=SubtitleResult,
    summary="Generate Subtitle File",
)
def generate_subtitles(
    request: SubtitleRequest,
):
    """
    Generate subtitle file from transcript segments.
    """

    try:

        result = service.generate(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )