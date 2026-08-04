"""
History Repository Contract.

Responsible for persisting completed, failed and cancelled
translation jobs for historical reporting and auditing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.translation_job import TranslationJob


class HistoryRepository(ABC):
    """
    Repository for archived translation jobs.
    """

    @abstractmethod
    def archive(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Archive a completed job.
        """

    @abstractmethod
    def find_by_id(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retrieve an archived job.
        """

    @abstractmethod
    def exists(
        self,
        job_id: str,
    ) -> bool:
        """
        Check whether an archived job exists.
        """

    @abstractmethod
    def list(
        self,
    ) -> list[TranslationJob]:
        """
        Return all archived jobs.
        """

    @abstractmethod
    def list_completed(
        self,
    ) -> list[TranslationJob]:
        """
        Return completed jobs.
        """

    @abstractmethod
    def list_failed(
        self,
    ) -> list[TranslationJob]:
        """
        Return failed jobs.
        """

    @abstractmethod
    def list_cancelled(
        self,
    ) -> list[TranslationJob]:
        """
        Return cancelled jobs.
        """

    @abstractmethod
    def delete(
        self,
        job_id: str,
    ) -> None:
        """
        Delete an archived job.
        """

    @abstractmethod
    def clear(
        self,
    ) -> None:
        """
        Remove all archived jobs.
        """

    @abstractmethod
    def count(
        self,
    ) -> int:
        """
        Return total archived jobs.
        """

    @abstractmethod
    def statistics(
        self,
    ) -> dict[str, int]:
        """
        Return archive statistics.

        Example
        -------
        {
            "completed": 120,
            "failed": 8,
            "cancelled": 4,
            "total": 132
        }
        """