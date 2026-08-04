"""
Exception raised when attempting to create a job that already exists.
"""

from __future__ import annotations

from .application_exception import ApplicationException


class DuplicateJobError(ApplicationException):
    """
    Raised when a job with the same identifier already exists.
    """

    status_code = 409
    error_code = "DUPLICATE_JOB"

    def __init__(
        self,
        job_id: str,
    ) -> None:
        super().__init__(
            message=f"Job '{job_id}' already exists.",
            details={
                "job_id": job_id,
            },
        )