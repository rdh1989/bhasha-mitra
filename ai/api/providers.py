"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : providers.py
Purpose     : AI Provider Management API

Description
-----------
Manage configured AI providers.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.provider.factory import ProviderFactory
from ai.provider.models import (
    ProviderSwitchRequest,
    ProviderSwitchResult,
)

router = APIRouter()

provider_manager = ProviderFactory.create()


# -----------------------------------------------------------------------------
# AI-014
# -----------------------------------------------------------------------------


@router.get(
    "/providers",
    summary="Available AI Providers",
)
def list_providers():
    """
    List available AI providers.
    """

    try:

        return provider_manager.list_providers()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# -----------------------------------------------------------------------------
# AI-015
# -----------------------------------------------------------------------------


@router.post(
    "/providers/switch",
    response_model=ProviderSwitchResult,
    summary="Switch AI Provider",
)
def switch_provider(
    request: ProviderSwitchRequest,
):
    """
    Switch configured AI provider.
    """

    try:

        return provider_manager.switch_provider(request)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )