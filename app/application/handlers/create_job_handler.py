"""
Application use case for creating a translation job.
"""

from domain.entities import TranslationJob

from app.application.dto.create_job_request import CreateJobRequest
from app.application.interfaces.job_repository import JobRepository
from app.application.validators.job_validator import JobValidator


class CreateJobHandler:
    """
    Handles the Create Translation Job use case.

    Workflow
    --------
    1. Validate request
    2. Create TranslationJob
    3. Persist job
    4. Return created job
    """

    def __init__(
        self,
        validator: JobValidator,
        job_repository: JobRepository,
    ) -> None:
        self._validator = validator
        self._job_repository = job_repository

    def handle(
        self,
        request: CreateJobRequest,
    ) -> TranslationJob:
        """
        Create a new translation job.
        """

        # ------------------------------------------
        # Validate request
        # ------------------------------------------

        self._validator.validate_create_request(
            request
        )

        # ------------------------------------------
        # Create domain entity
        # ------------------------------------------

        job = TranslationJob(
            input_file=request.input_file,
            source_language=request.source_language,
            target_language=request.target_language,
            priority=request.priority,
        )

        # ------------------------------------------
        # Persist
        # ------------------------------------------

        self._job_repository.save(job)

        return job