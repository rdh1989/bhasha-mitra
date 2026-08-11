from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.api.routes.job import get_job
from app.api.routes.translations import get_translations
from domain.entities import TranslationJob


class FakeJobService:
    def __init__(self, jobs):
        self._jobs = {job.id: job for job in jobs}

    def get(self, job_id):
        return self._jobs.get(job_id)

    def list_all(self):
        return list(self._jobs.values())


class FakeContainer:
    def __init__(self, jobs):
        self.job_service = FakeJobService(jobs)


def test_get_job_returns_persisted_preprocessing_stage():
    job = TranslationJob(
        input_file=Path("demo.mp4"),
        source_language="en",
        target_language="mr",
    )
    job.mark_audio_extracted(Path("demo.wav"))

    response = get_job(job.id, FakeContainer([job]))

    assert response["success"] is True
    assert response["job"]["job_id"] == job.id
    assert response["job"]["status"] == "PENDING"
    assert response["job"]["display_stage"] == "Speech Recognition"
    assert response["job"]["display_progress"] == 40


@pytest.mark.anyio
async def test_get_translations_returns_real_jobs_sorted_latest_first():
    older = TranslationJob(
        input_file=Path("older.mp4"),
        source_language="en",
        target_language="mr",
    )
    older.updated_at = datetime(2026, 8, 10, tzinfo=UTC)
    older.created_at = datetime(2026, 8, 10, tzinfo=UTC)

    newer = TranslationJob(
        input_file=Path("newer.mp4"),
        source_language="en",
        target_language="hi",
    )
    newer.mark_audio_extracted(Path("newer.wav"))
    newer.mark_asr_completed(Path("newer.json"))
    newer.queue()
    newer.updated_at = datetime(2026, 8, 11, tzinfo=UTC)
    newer.created_at = datetime(2026, 8, 11, tzinfo=UTC)

    response = await get_translations(FakeContainer([older, newer]))

    assert response["success"] is True
    assert response["count"] == 2
    assert response["translations"][0]["job_id"] == newer.id
    assert response["translations"][0]["status"] == "QUEUED"
    assert response["translations"][0]["display_stage"] == "Queued For Translation"
