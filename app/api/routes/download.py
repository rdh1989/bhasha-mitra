"""
Download API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Path, status

router = APIRouter(tags=["Download"])


@router.get(
    "/download/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Download translated output",
)
async def download_output(
    job_id: str = Path(
        ...,
        description="Unique job identifier.",
    ),
) -> dict:
    """
    Download the translated output for a completed job.

    This endpoint is currently a stub.
    Business logic will be implemented in DownloadController.
    """

    # TODO: Delegate to DownloadController

    return {
        "success": True,
        "job_id": job_id,
        "message": "Download API not implemented.",
        "download_url": None,
    }