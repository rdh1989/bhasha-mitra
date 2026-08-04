"""
Model API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter(tags=["Models"])


@router.get(
    "/models",
    status_code=status.HTTP_200_OK,
    summary="Get installed AI models",
)
async def get_models() -> dict:
    """
    Retrieve the list of installed AI models.

    This endpoint is currently a stub.
    Business logic will be implemented in ModelController.
    """

    # TODO: Delegate to ModelController

    return {
        "success": True,
        "models": [],
        "message": "Models API not implemented.",
    }