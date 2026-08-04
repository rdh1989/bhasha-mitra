"""
Repository contract for TranslationJob persistence.
"""

from abc import ABC
from abc import abstractmethod
from pathlib import Path

from domain.entities import TranslationJob


class JobRepository(ABC):
    """
    Contract for TranslationJob persistence.
    """

    @abstractmethod
    def save(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Persist a TranslationJob.
        """
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retrieve a job by ID.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        job_id: str,
    ) -> None:
        """
        Delete a job.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        job_id: str,
    ) -> bool:
        """
        Returns True if a job exists.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(
        self,
    ) -> list[TranslationJob]:
        """
        Return all jobs.
        """
        raise NotImplementedError

    @abstractmethod
    def find_active_job(
        self,
        input_file: Path,
    ) -> TranslationJob | None:
        """
        Return an active job for the given
        input file if one exists.
        """
        raise NotImplementedError