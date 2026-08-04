"""
Application service for Translation Job operations.
"""

from pathlib import Path

from domain.entities import TranslationJob

from app.application.dto.create_job_request import CreateJobRequest

from app.application.handlers.cancel_job_handler import CancelJobHandler
from app.application.handlers.complete_job_handler import CompleteJobHandler
from app.application.handlers.create_job_handler import CreateJobHandler
from app.application.handlers.delete_job_handler import DeleteJobHandler
from app.application.handlers.fail_job_handler import FailJobHandler
from app.application.handlers.get_job_handler import GetJobHandler
from app.application.handlers.list_jobs_handler import ListJobsHandler
from app.application.handlers.queue_job_handler import QueueJobHandler
from app.application.handlers.retry_job_handler import RetryJobHandler
from app.application.handlers.start_job_handler import StartJobHandler
from app.application.handlers.update_progress_handler import (
    UpdateProgressHandler,
)


class JobService:
    """
    Facade for Translation Job application use cases.
    """

    def __init__(
        self,
        create_handler: CreateJobHandler,
        get_handler: GetJobHandler,
        list_handler: ListJobsHandler,
        delete_handler: DeleteJobHandler,
        queue_handler: QueueJobHandler,
        start_handler: StartJobHandler,
        complete_handler: CompleteJobHandler,
        fail_handler: FailJobHandler,
        retry_handler: RetryJobHandler,
        cancel_handler: CancelJobHandler,
        update_progress_handler: UpdateProgressHandler,
    ) -> None:
        self._create_handler = create_handler
        self._get_handler = get_handler
        self._list_handler = list_handler
        self._delete_handler = delete_handler
        self._queue_handler = queue_handler
        self._start_handler = start_handler
        self._complete_handler = complete_handler
        self._fail_handler = fail_handler
        self._retry_handler = retry_handler
        self._cancel_handler = cancel_handler
        self._update_progress_handler = update_progress_handler

    def create(
        self,
        request: CreateJobRequest,
    ) -> TranslationJob:
        return self._create_handler.handle(request)

    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        return self._get_handler.handle(job_id)

    def list_all(
        self,
    ) -> list[TranslationJob]:
        return self._list_handler.handle()

    def delete(
        self,
        job_id: str,
    ) -> bool:
        return self._delete_handler.handle(job_id)

    def queue(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        return self._queue_handler.handle(job_id)

    def start(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        return self._start_handler.handle(job_id)

    def complete(
        self,
        job_id: str,
        output_file: Path,
    ) -> TranslationJob | None:
        return self._complete_handler.handle(
            job_id,
            output_file,
        )

    def fail(
        self,
        job_id: str,
        error_message: str,
    ) -> TranslationJob | None:
        return self._fail_handler.handle(
            job_id,
            error_message,
        )

    def retry(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        return self._retry_handler.handle(job_id)

    def cancel(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        return self._cancel_handler.handle(job_id)

    def update_progress(
        self,
        job_id: str,
        stage: str,
        percentage: int,
        message: str = "",
    ) -> TranslationJob | None:
        return self._update_progress_handler.handle(
            job_id,
            stage,
            percentage,
            message,
        )