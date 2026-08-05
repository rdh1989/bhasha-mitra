"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : translation.py
Purpose     : Translation API

Description
-----------
REST endpoints for text translation.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.translation.models import TranslationRequest

from ai.core.service_registry import ServiceRegistry



router = APIRouter()


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------


service = ServiceRegistry.translation_service()

# --------------------------------------------------------------------------
# AI-006
# --------------------------------------------------------------------------


@router.post(
    "/translate",
    summary="Translate Text",
)
def translate(
    request: TranslationRequest,
):
    """
    Translate text between languages.
    """

    try:

        result = service.translate(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )