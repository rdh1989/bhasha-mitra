"""
Application use case for listing translation jobs.
"""

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class ListJobsHandler:
    """
    Handles the List Translation Jobs use case.

    Workflow
    --------
    1. Retrieve all jobs from repository
    2. Return the collection
    """

    def __init__(
        self,
        job_repository: JobRepository,
    ) -> None:
        self._job_repository = job_repository

    def handle(
        self,
    ) -> list[TranslationJob]:
        """
        Retrieve all translation jobs.

        Returns:
            List of TranslationJob entities.
        """

        return self._job_repository.list_all()