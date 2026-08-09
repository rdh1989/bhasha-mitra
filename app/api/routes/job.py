"""
===============================================================================
BHASHA MITRA
Job API
===============================================================================

Module:
    jobs.py

Layer:
    Presentation / API

Description:
    Provides APIs for controlling translation jobs.

Responsibilities:
    - Start a translation job
    - Queue the job for translation
    - Allow translation to wait for background preprocessing

Important:
    Translation starts only when the user explicitly requests it.

    If preprocessing is still running, the translation request is queued.
    The TranslationWorker is responsible for waiting until preprocessing
    is completed before starting translation.

    If preprocessing fails, translation must not start.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)

from .upload import (
    get_application_container,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.post(
    "/{job_id}/start",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start translation",
)
def start_translation(
    job_id: str,
    container: ApplicationContainer = Depends(
        get_application_container
    ),
) -> dict:
    """
    Request translation for an existing job.

    Translation is queued immediately.

    If preprocessing is still running, the TranslationWorker waits
    for preprocessing to complete before starting translation.
    """

    # =========================================================================
    # Get job
    # =========================================================================

    job = container.job_repository.get(
        job_id
    )

    if job is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation job not found.",
        )

    # =========================================================================
    # Queue translation request
    # =========================================================================

    try:

        container.job_service.queue(
            job_id
        )

        container.translation_queue.put(
            job_id
        )

    except Exception as exc:

        logger.exception(
            "Failed to queue translation | job_id=%s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation could not be started.",
        ) from exc

    logger.info(
        "Translation requested | job_id=%s | "
        "preprocessing_audio=%s | preprocessing_asr=%s",
        job_id,
        job.preprocessing.audio_extracted,
        job.preprocessing.asr_completed,
    )

    # =========================================================================
    # Response
    # =========================================================================

    return {
        "success": True,
        "job_id": job.id,
    }