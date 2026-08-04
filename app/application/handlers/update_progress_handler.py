"""
Application use case for updating translation job progress.
"""

from domain.entities import TranslationJob

from app.application.interfaces.job_repository import JobRepository


class UpdateProgressHandler:
    """
    Handles the Update Translation Job Progress use case.

    Workflow
    --------
    1. Retrieve job
    2. Update progress
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
        stage: str,
        percentage: int,
        message: str = "",
    ) -> TranslationJob | None:
        """
        Update the progress of a translation job.

        Args:
            job_id: Translation job identifier.
            stage: Current processing stage.
            percentage: Completion percentage.
            message: Optional progress message.

        Returns:
            Updated TranslationJob if found,
            otherwise None.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            return None

        job.update_progress(
            stage=stage,
            percentage=percentage,
            message=message,
        )

        self._job_repository.save(job)

        return job