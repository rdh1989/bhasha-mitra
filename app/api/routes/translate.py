"""
Translation API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter(tags=["Translation"])


@router.post(
    "/translate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start translation job",
)
async def start_translation() -> dict:
    """
    Start a new translation job.

    This endpoint is currently a stub.
    Business logic will be implemented in TranslateController.
    """

    # TODO: Delegate to TranslateController

    return {
        "success": True,
        "message": "Translation API not implemented.",
        "job_id": None,
        "status": "pending",
    }