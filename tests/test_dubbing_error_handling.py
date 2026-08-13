from pathlib import Path
import json

from domain.entities import TranslationJob
from domain.enums.job_status import JobStatus
from infrastructure.ai.dubbing_client import DubbingClient
from workers.dubbing_worker import DubbingWorker
from workers.job_queue import JobQueue


class InMemoryJobRepository:
    def __init__(self, job: TranslationJob) -> None:
        self._job = job

    def get(self, job_id: str) -> TranslationJob | None:
        if self._job.id == job_id:
            return self._job
        return None

    def save(self, job: TranslationJob) -> None:
        self._job = job


def test_dubbing_client_extracts_detail_from_error_payload() -> None:
    detail = DubbingClient._extract_error_detail(
        {
            "detail": (
                "Translation segments contain overlapping "
                "timestamps around segment 7."
            )
        }
    )

    assert (
        detail
        == "Translation segments contain overlapping "
        "timestamps around segment 7."
    )


def test_dubbing_worker_marks_completed_job_as_failed() -> None:
    job = TranslationJob(
        input_file=Path("demo.mp4"),
        source_language="en",
        target_language="mr",
    )
    job.queue()
    job.start()
    job.complete(output_file=Path("translation.json"))

    repository = InMemoryJobRepository(job)
    worker = DubbingWorker(
        job_queue=JobQueue[str](),
        export_queue=JobQueue[str](),
        job_repository=repository,
        dubbing_client=None,  # type: ignore[arg-type]
        path_manager=None,  # type: ignore[arg-type]
        voice="mr_IN-google-medium",
    )

    error_message = (
        "Dubbing API returned HTTP 400: "
        "Translation segments contain overlapping timestamps "
        "around segment 7."
    )

    worker._mark_failed(
        job_id=job.id,
        error_message=error_message,
    )

    updated = repository.get(job.id)

    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_message == error_message


def test_dubbing_worker_normalizes_overlapping_timestamps(
    tmp_path: Path,
) -> None:
    translation_file = tmp_path / "translation.json"

    translation_file.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 1.0,
                        "translated_text": "Hello",
                    },
                    {
                        "id": 2,
                        "start": 0.9,
                        "end": 1.5,
                        "translated_text": "World",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    job = TranslationJob(
        input_file=Path("demo.mp4"),
        source_language="en",
        target_language="mr",
    )

    worker = DubbingWorker(
        job_queue=JobQueue[str](),
        export_queue=JobQueue[str](),
        job_repository=InMemoryJobRepository(job),
        dubbing_client=None,  # type: ignore[arg-type]
        path_manager=None,  # type: ignore[arg-type]
        voice="mr_IN-google-medium",
    )

    normalized_path = worker._normalize_translation_timestamps(
        translation_file=translation_file,
        job_id=job.id,
    )

    assert normalized_path != translation_file

    payload = json.loads(
        normalized_path.read_text(encoding="utf-8")
    )
    segments = payload["segments"]

    assert segments[0]["end"] <= segments[1]["start"]
