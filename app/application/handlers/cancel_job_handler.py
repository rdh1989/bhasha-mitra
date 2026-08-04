"""
Application use case for cancelling a translation job.
"""

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class CancelJobHandler:
    """
    Handles the Cancel Translation Job use case.

    Workflow
    --------
    1. Retrieve job
    2. Cancel job
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
    ) -> TranslationJob | None:
        """
        Cancel a translation job.

        Returns:
            Updated TranslationJob if found,
            otherwise None.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            return None

        job.cancel()

        self._job_repository.save(job)

        return job