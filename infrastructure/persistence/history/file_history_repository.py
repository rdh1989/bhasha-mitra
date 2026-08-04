"""
Local filesystem implementation of HistoryRepository.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.application.interfaces.history_repository import HistoryRepository
from app.application.interfaces.storage_service import StorageService
from domain.entities.translation_job import TranslationJob
from domain.enums.job_status import JobStatus
from infrastructure.filesystem.path_manager import PathManager
from infrastructure.persistence.serializers.history_serializer import (
    HistorySerializer,
)


class FileHistoryRepository(HistoryRepository):
    """
    Persists archived TranslationJob instances.
    """

    def __init__(
        self,
        storage: StorageService,
        path_manager: PathManager,
    ) -> None:

        self._storage = storage
        self._paths = path_manager

        self._completed = self._paths.history / "completed"
        self._failed = self._paths.history / "failed"
        self._cancelled = self._paths.history / "cancelled"

        for directory in (
            self._completed,
            self._failed,
            self._cancelled,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _directory(
        self,
        status: JobStatus,
    ) -> Path:

        if status == JobStatus.COMPLETED:
            return self._completed

        if status == JobStatus.FAILED:
            return self._failed

        return self._cancelled

    def _job_file(
        self,
        job: TranslationJob,
    ) -> Path:

        return self._directory(job.status) / f"{job.job_id}.json"

    # ---------------------------------------------------------
    # Repository
    # ---------------------------------------------------------

    def archive(
        self,
        job: TranslationJob,
    ) -> None:

        file = self._job_file(job)

        data = HistorySerializer.serialize(job)

        file.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def find_by_id(
        self,
        job_id: str,
    ) -> TranslationJob | None:

        for directory in (
            self._completed,
            self._failed,
            self._cancelled,
        ):

            file = directory / f"{job_id}.json"

            if file.exists():

                return HistorySerializer.deserialize(
                    json.loads(
                        file.read_text(
                            encoding="utf-8",
                        )
                    )
                )

        return None

    def exists(
        self,
        job_id: str,
    ) -> bool:

        return self.find_by_id(job_id) is not None

    def list(
        self,
    ) -> list[TranslationJob]:

        return (
            self.list_completed()
            + self.list_failed()
            + self.list_cancelled()
        )

    def list_completed(
        self,
    ) -> list[TranslationJob]:

        return self._load_directory(self._completed)

    def list_failed(
        self,
    ) -> list[TranslationJob]:

        return self._load_directory(self._failed)

    def list_cancelled(
        self,
    ) -> list[TranslationJob]:

        return self._load_directory(self._cancelled)

    def delete(
        self,
        job_id: str,
    ) -> None:

        for directory in (
            self._completed,
            self._failed,
            self._cancelled,
        ):

            file = directory / f"{job_id}.json"

            if file.exists():
                file.unlink()

    def clear(
        self,
    ) -> None:

        for job in self.list():
            self.delete(job.job_id)

    def count(
        self,
    ) -> int:

        return len(self.list())

    def statistics(
        self,
    ) -> dict[str, int]:

        completed = len(self.list_completed())
        failed = len(self.list_failed())
        cancelled = len(self.list_cancelled())

        return {
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "total": completed + failed + cancelled,
        }

    # ---------------------------------------------------------
    # Internal
    # ---------------------------------------------------------

    def _load_directory(
        self,
        directory: Path,
    ) -> list[TranslationJob]:

        jobs: list[TranslationJob] = []

        for file in directory.glob("*.json"):

            jobs.append(
                HistorySerializer.deserialize(
                    json.loads(
                        file.read_text(
                            encoding="utf-8",
                        )
                    )
                )
            )

        return jobs