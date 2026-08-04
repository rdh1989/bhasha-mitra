"""
Provider API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter(tags=["Providers"])


@router.get(
    "/providers",
    status_code=status.HTTP_200_OK,
    summary="Get available providers",
)
async def get_providers() -> dict:
    """
    Retrieve the list of available providers.

    This endpoint is currently a stub.
    Business logic will be implemented in ProviderController.
    """

    # TODO: Delegate to ProviderController

    return {
        "success": True,
        "providers": [],
        "message": "Providers API not implemented.",
    }