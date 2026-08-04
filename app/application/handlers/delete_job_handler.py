"""
Application use case for deleting a translation job.
"""

from app.application.interfaces.job_repository import JobRepository


class DeleteJobHandler:
    """
    Handles the Delete Translation Job use case.

    Workflow
    --------
    1. Check if job exists
    2. Delete job
    3. Return success status
    """

    def __init__(
        self,
        job_repository: JobRepository,
    ) -> None:
        self._job_repository = job_repository

    def handle(
        self,
        job_id: str,
    ) -> bool:
        """
        Delete a translation job.

        Returns:
            True if the job was deleted,
            False if the job does not exist.
        """

        if not self._job_repository.exists(job_id):
            return False

        self._job_repository.delete(job_id)

        return True