"""
===============================================================================
BHASHA MITRA
Start Translation Job Handler
===============================================================================

Module:
    start_job_handler.py

Layer:
    Application

Description:
    Handles the Start Translation Job use case.

Responsibilities:
    - Retrieve the translation job
    - Queue the job for processing
    - Persist the updated job
    - Return the queued job

Lifecycle:
    PENDING / RETRYING
            ↓
          QUEUED

The worker is responsible for moving the job from QUEUED to RUNNING.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import logging

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


logger = logging.getLogger(__name__)


class StartJobHandler:
    """
    Handles the Start Translation Job use case.
    """

    def __init__(
        self,
        job_repository: JobRepository,
    ) -> None:
        self._job_repository = job_repository

    def handle(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Queue a translation job for processing.

        The actual processing is performed by the worker.

        Returns:
            Updated TranslationJob if found,
            otherwise None.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            logger.warning(
                "Translation job not found | job_id=%s",
                job_id,
            )
            return None

        logger.info(
            "Queueing translation job | job_id=%s | status=%s",
            job.id,
            job.status.value,
        )

        job.queue()

        self._job_repository.save(job)

        logger.info(
            "Translation job queued | job_id=%s | status=%s",
            job.id,
            job.status.value,
        )

        return job