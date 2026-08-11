"""
Translation History API routes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)

from .job import _serialize_job
from .upload import get_application_container

router = APIRouter(tags=["Translation History"])

logger = logging.getLogger(__name__)


@router.get(
    "/translations",
    status_code=status.HTTP_200_OK,
    summary="Get translation history",
)
async def get_translations(
    container: ApplicationContainer = Depends(
        get_application_container
    ),
) -> dict:
    """
    Return all translation jobs.
    """

    logger.info(
        "TRANSLATION HISTORY REQUESTED"
    )

    jobs = sorted(
        container.job_service.list_all(),
        key=lambda job: job.created_at,
        reverse=True,
    )

    translations = [
        _serialize_job(job)
        for job in jobs
    ]

    logger.info(
        "TRANSLATION HISTORY RETURNED | count=%s",
        len(translations),
    )

    return {
        "success": True,
        "count": len(translations),
        "translations": translations,
    }