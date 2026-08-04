"""
Local filesystem implementation of JobRepository.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository
from app.application.interfaces.storage_service import StorageService
from domain.entities.translation_job import TranslationJob
from infrastructure.filesystem.path_manager import PathManager
from infrastructure.persistence.serializers.job_serializer import (
    JobSerializer,
)


class FileJobRepository(JobRepository):
    """
    Persists TranslationJob instances as JSON files.
    """

    def __init__(
        self,
        storage: StorageService,
        path_manager: PathManager,
    ) -> None:

        self._storage = storage
        self._paths = path_manager

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _job_file(
        self,
        job_id: str,
    ) -> Path:

        return self._paths.jobs / f"{job_id}.json"

    # ----------------------------------------------------------
    # Repository
    # ----------------------------------------------------------

    def save(
        self,
        job: TranslationJob,
    ) -> None:

        file = self._job_file(job.job_id)

        data = JobSerializer.serialize(job)

        file.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:

        file = self._job_file(job_id)

        if not file.exists():
            return None

        data = json.loads(
            file.read_text(
                encoding="utf-8",
            )
        )

        return JobSerializer.deserialize(data)

    def delete(
        self,
        job_id: str,
    ) -> None:

        file = self._job_file(job_id)

        if file.exists():
            file.unlink()

    def exists(
        self,
        job_id: str,
    ) -> bool:

        return self._job_file(job_id).exists()

    def list_all(
        self,
    ) -> list[TranslationJob]:

        jobs: list[TranslationJob] = []

        for file in self._paths.jobs.glob("*.json"):

            data = json.loads(
                file.read_text(
                    encoding="utf-8",
                )
            )

            jobs.append(
                JobSerializer.deserialize(data)
            )

        return jobs

    def find_active_job(
        self,
        input_file: Path,
    ) -> TranslationJob | None:

        for job in self.list_all():

            if (
                Path(job.input_file) == input_file
                and not job.is_finished
            ):
                return job

        return None