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
from pathlib import Path

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


def _serialize_job(job) -> dict:
    payload = job.to_dict()
    preprocessing = payload["preprocessing"]
    progress = payload["progress"]
    status = payload["status"]

    display_stage = progress.get("stage") or "Pending"
    display_progress = progress.get("percentage", 0)

    if status == "PENDING":
        display_stage = "Preparing"
        display_progress = max(display_progress, 5)

    if not preprocessing.get("audio_extracted"):
        display_stage = "Extracting Audio"
        display_progress = max(display_progress, 15)
    elif not preprocessing.get("asr_completed"):
        display_stage = "Speech Recognition"
        display_progress = max(display_progress, 40)
    elif status == "QUEUED":
        display_stage = "Queued For Translation"
        display_progress = max(display_progress, 65)
    elif status == "RUNNING":
        display_stage = (
            display_stage
            if display_stage not in {"Pending", "Preparing"}
            else "Translation"
        )
        display_progress = max(display_progress, 80)
    elif status == "COMPLETED":
        display_stage = "Completed"
        display_progress = 100
    elif status == "FAILED":
        display_stage = "Failed"
    elif status == "CANCELLED":
        display_stage = "Cancelled"

    payload.update(
        {
            "job_id": job.id,
            "file_name": Path(payload["input_file"]).name,
            "display_stage": display_stage,
            "display_progress": display_progress,
        }
    )

    return payload


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get translation job",
)
def get_job(
    job_id: str,
    container: ApplicationContainer = Depends(
        get_application_container
    ),
) -> dict:
    logger.info(
        "TRANSLATION JOB STATUS REQUESTED | job_id=%s",
        job_id,
    )

    job = container.job_service.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation job not found.",
        )

    payload = _serialize_job(job)

    logger.info(
        "TRANSLATION JOB STATUS RETURNED | job_id=%s | status=%s | stage=%s",
        job_id,
        payload["status"],
        payload["display_stage"],
    )

    return {
        "success": True,
        "job": payload,
    }


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

    logger.info(
        "TRANSLATION START REQUESTED | job_id=%s",
        job_id,
    )

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

    queued_job = container.job_service.get(job_id)

    return {
        "success": True,
        "job_id": job.id,
        "status": (
            queued_job.status.value
            if queued_job is not None
            else job.status.value
        ),
    }