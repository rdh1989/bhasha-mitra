"""
Application use case for failing a translation job.
"""

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class FailJobHandler:
    """
    Handles the Fail Translation Job use case.

    Workflow
    --------
    1. Retrieve job
    2. Mark job as failed
    3. Persist updated job
    4. Return updated job
    """

    def __init__(
        self,
        job_repository: JobRepository,
    ) -> None:
        self._job_repository = job_repository

    def handle(
        self,
        job_id: str,
        error_message: str,
    ) -> TranslationJob | None:
        """
        Mark a translation job as failed.

        Args:
            job_id: Translation job identifier.
            error_message: Reason for failure.

        Returns:
            Updated TranslationJob if found,
            otherwise None.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            return None

        job.fail(error_message)

        self._job_repository.save(job)

        return job