"""
Application orchestrator for the complete translation workflow.
"""

from pathlib import Path

from domain.entities import TranslationJob

from app.application.dto.create_job_request import CreateJobRequest
from app.application.services.job_service import JobService


class TranslationOrchestrator:
    """
    Orchestrates the complete translation workflow.

    Responsibilities
    ----------------
    • Create translation job
    • Queue translation job
    • Start translation job
    • Coordinate AI pipeline (future)
    • Complete or fail translation job
    """

    def __init__(
        self,
        job_service: JobService,
    ) -> None:
        self._job_service = job_service

    def create_job(
        self,
        request: CreateJobRequest,
    ) -> TranslationJob:
        """
        Create a new translation job.
        """

        return self._job_service.create(request)

    def queue_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Queue a translation job.
        """

        return self._job_service.queue(job_id)

    def start_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Start processing a translation job.
        """

        return self._job_service.start(job_id)

    def update_progress(
        self,
        job_id: str,
        stage: str,
        percentage: int,
        message: str = "",
    ) -> TranslationJob | None:
        """
        Update translation progress.
        """

        return self._job_service.update_progress(
            job_id=job_id,
            stage=stage,
            percentage=percentage,
            message=message,
        )

    def complete_job(
        self,
        job_id: str,
        output_file: Path,
    ) -> TranslationJob | None:
        """
        Mark translation as completed.
        """

        return self._job_service.complete(
            job_id,
            output_file,
        )

    def fail_job(
        self,
        job_id: str,
        error_message: str,
    ) -> TranslationJob | None:
        """
        Mark translation as failed.
        """

        return self._job_service.fail(
            job_id,
            error_message,
        )

    def cancel_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Cancel a translation job.
        """

        return self._job_service.cancel(job_id)

    def retry_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retry a failed translation job.
        """

        return self._job_service.retry(job_id)