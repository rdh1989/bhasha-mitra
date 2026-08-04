"""
Application use case for retrieving a translation job.
"""

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class GetJobHandler:
    """
    Handles the Get Translation Job use case.

    Workflow
    --------
    1. Retrieve job from repository
    2. Return job
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
        Retrieve a translation job by its ID.

        Returns:
            TranslationJob if found, otherwise None.
        """

        return self._job_repository.get(job_id)