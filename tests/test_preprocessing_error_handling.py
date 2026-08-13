from pathlib import Path

from domain.entities import TranslationJob
from domain.enums.job_status import JobStatus
from workers.job_queue import JobQueue
from workers.preprocessing_worker import PreprocessingWorker


class InMemoryJobRepository:
    def __init__(self, job: TranslationJob) -> None:
        self._job = job

    def get(self, job_id: str) -> TranslationJob | None:
        if self._job.id == job_id:
            return self._job
        return None

    def save(self, job: TranslationJob) -> None:
        self._job = job


def test_preprocessing_worker_marks_pending_job_failed() -> None:
    job = TranslationJob(
        input_file=Path("demo.mp4"),
        source_language="en",
        target_language="mr",
    )

    repository = InMemoryJobRepository(job)

    worker = PreprocessingWorker(
        job_queue=JobQueue[str](),
        translation_queue=JobQueue[str](),
        job_repository=repository,
        audio_extractor=None,  # type: ignore[arg-type]
        transcript_client=None,  # type: ignore[arg-type]
        language_detection_client=None,  # type: ignore[arg-type]
        path_manager=None,  # type: ignore[arg-type]
        queue_job_handler=None,  # type: ignore[arg-type]
    )

    worker._mark_failed(
        job_id=job.id,
        error_message="Model 'asr:small' is not loaded.",
    )

    updated = repository.get(job.id)

    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_message == "Model 'asr:small' is not loaded."
