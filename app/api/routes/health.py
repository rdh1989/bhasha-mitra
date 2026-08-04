"""
Health API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def health_check() -> dict:
    """
    Check the health status of the application.

    This endpoint is currently a stub.
    Business logic will be implemented in HealthController.
    """

    # TODO: Delegate to HealthController

    return {
        "success": True,
        "status": "healthy",
        "application": "Bhasha Mitra",
        "version": "1.0.0",
        "message": "Health API is operational.",
    }