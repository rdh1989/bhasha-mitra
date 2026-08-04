"""
Application use case for completing a translation job.
"""

from pathlib import Path

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class CompleteJobHandler:
    """
    Handles the Complete Translation Job use case.

    Workflow
    --------
    1. Retrieve job
    2. Complete job
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
        output_file: Path,
    ) -> TranslationJob | None:
        """
        Complete a translation job.

        Args:
            job_id: Translation job identifier.
            output_file: Generated translated video file.

        Returns:
            Updated TranslationJob if found,
            otherwise None.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            return None

        job.complete(output_file)

        self._job_repository.save(job)

        return job