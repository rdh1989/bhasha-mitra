"""
===============================================================================
BHASHA MITRA
File Job Repository
===============================================================================

Description:
    File-based persistence implementation for TranslationJob.

Responsibilities:
    - Persist translation jobs as JSON
    - Retrieve jobs by ID
    - Delete jobs
    - List jobs
    - Find active jobs for an input file

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository
from domain.entities import TranslationJob
from domain.enums.job_priority import JobPriority
from domain.enums.job_status import JobStatus
from domain.value_objects.job_progress import JobProgress


logger = logging.getLogger(__name__)


class FileJobRepository(JobRepository):
    """
    Stores TranslationJob objects as JSON files.
    """

    def __init__(
        self,
        storage_directory: Path,
    ) -> None:

        self._storage_directory = storage_directory

        self._storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "File job repository initialized | path=%s",
            self._storage_directory,
        )

    def save(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Persist a TranslationJob.
        """

        file_path = self._get_file_path(job.id)

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                job.to_dict(),
                file,
                indent=4,
                ensure_ascii=False,
            )

        logger.debug(
            "Job persisted | job_id=%s | status=%s",
            job.id,
            job.status.value,
        )

    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retrieve a job by ID.
        """

        file_path = self._get_file_path(job_id)

        if not file_path.exists():

            logger.debug(
                "Job not found | job_id=%s",
                job_id,
            )

            return None

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        job = self._build_job(data)

        logger.debug(
            "Job loaded | job_id=%s | status=%s",
            job.id,
            job.status.value,
        )

        return job

    def delete(
        self,
        job_id: str,
    ) -> None:
        """
        Delete a job.
        """

        file_path = self._get_file_path(job_id)

        if not file_path.exists():
            return

        file_path.unlink()

        logger.info(
            "Job deleted | job_id=%s",
            job_id,
        )

    def exists(
        self,
        job_id: str,
    ) -> bool:
        """
        Return True if a job exists.
        """

        return self._get_file_path(job_id).exists()

    def list_all(
        self,
    ) -> list[TranslationJob]:
        """
        Return all stored jobs.
        """

        jobs: list[TranslationJob] = []

        for file_path in sorted(
            self._storage_directory.glob("*.json")
        ):

            with file_path.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            jobs.append(
                self._build_job(data)
            )

        logger.debug(
            "Jobs loaded | count=%s",
            len(jobs),
        )

        return jobs

    def find_active_job(
        self,
        input_file: Path,
    ) -> TranslationJob | None:
        """
        Return an active job for the given input file.
        """

        for job in self.list_all():

            if (
                job.input_file == input_file
                and not job.is_finished
            ):

                logger.debug(
                    "Active job found | job_id=%s",
                    job.id,
                )

                return job

        return None

    def _get_file_path(
        self,
        job_id: str,
    ) -> Path:
        """
        Return the JSON file path.
        """

        return (
            self._storage_directory
            / f"{job_id}.json"
        )

    def _build_job(
        self,
        data: dict,
    ) -> TranslationJob:
        """
        Reconstruct a TranslationJob from JSON.
        """

        progress = JobProgress(
            stage=data["progress"]["stage"],
            percentage=data["progress"]["percentage"],
            message=data["progress"]["message"],
        )

        job = TranslationJob(
            input_file=Path(data["input_file"]),
            source_language=data["source_language"],
            target_language=data["target_language"],
            id=data["id"],
            priority=JobPriority[
                data["priority"]
            ],
            status=JobStatus(
                data["status"]
            ),
            progress=progress,
            retry_count=data["retry_count"],
            output_file=(
                Path(data["output_file"])
                if data["output_file"]
                else None
            ),
            error_message=data["error_message"],
            created_at=datetime.fromisoformat(
                data["created_at"]
            ),
            started_at=(
                datetime.fromisoformat(
                    data["started_at"]
                )
                if data["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromisoformat(
                    data["completed_at"]
                )
                if data["completed_at"]
                else None
            ),
            cancelled_at=(
                datetime.fromisoformat(
                    data["cancelled_at"]
                )
                if data["cancelled_at"]
                else None
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"]
            ),
        )

        job.clear_events()

        return job