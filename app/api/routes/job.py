"""
Job API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Path, status

router = APIRouter(tags=["Jobs"])


@router.get(
    "/job/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get job status",
)
async def get_job_status(
    job_id: str = Path(
        ...,
        description="Unique job identifier.",
    ),
) -> dict:
    """
    Retrieve the current status of a translation job.

    This endpoint is currently a stub.
    Business logic will be implemented in JobController.
    """

    # TODO: Delegate to JobController

    return {
        "success": True,
        "job_id": job_id,
        "status": "pending",
        "message": "Job status API not implemented.",
    }


@router.delete(
    "/job/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job",
)
async def delete_job(
    job_id: str = Path(
        ...,
        description="Unique job identifier.",
    ),
) -> dict:
    """
    Delete or cancel a translation job.

    This endpoint is currently a stub.
    Business logic will be implemented in JobController.
    """

    # TODO: Delegate to JobController

    return {
        "success": True,
        "job_id": job_id,
        "message": "Delete Job API not implemented.",
    }