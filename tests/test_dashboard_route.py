from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from domain.entities import TranslationJob
from frontend.pages import routes
from frontend.pages.routes import render_dashboard


class FakeJobService:
    def __init__(self, jobs):
        self._jobs = jobs

    def list_all(self):
        return list(self._jobs)


def _request_with_jobs(jobs):
    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory="frontend/static"),
        name="static",
    )
    app.state.application_container = SimpleNamespace(
        job_service=FakeJobService(jobs)
    )
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/dashboard",
        "headers": [],
        "app": app,
        "query_string": b"",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    request = Request(scope)
    request.state.user = SimpleNamespace(
        username="admin",
        role="admin",
    )
    return request


def test_render_dashboard_uses_database_counts_and_recent_jobs():
    completed = TranslationJob(
        input_file=Path("completed.mp4"),
        source_language="en",
        target_language="mr",
    )
    completed.mark_audio_extracted(Path("completed.wav"))
    completed.mark_asr_completed(Path("completed.json"))
    completed.queue()
    completed.start()
    completed.complete(Path("translation.json"))
    completed.updated_at = datetime(2026, 8, 10, tzinfo=UTC)

    running = TranslationJob(
        input_file=Path("running.mp4"),
        source_language="en",
        target_language="hi",
    )
    running.mark_audio_extracted(Path("running.wav"))
    running.mark_asr_completed(Path("running.json"))
    running.queue()
    running.start()
    running.update_progress(
        stage="Translation",
        percentage=82,
        message="Running",
    )
    running.updated_at = datetime(2026, 8, 11, tzinfo=UTC)

    failed = TranslationJob(
        input_file=Path("failed.mp4"),
        source_language="en",
        target_language="ta",
    )
    failed.mark_audio_extracted(Path("failed.wav"))
    failed.mark_asr_completed(Path("failed.json"))
    failed.queue()
    failed.start()
    failed.fail("boom")
    failed.updated_at = datetime(2026, 8, 9, tzinfo=UTC)

    routes._build_system_information = lambda: {
        "cpu_usage": "11.0%",
        "memory_usage": "52.5%",
        "gpu_usage": "7%",
        "disk_usage": "39.3%",
    }

    request = _request_with_jobs([completed, running, failed])

    response = render_dashboard(request)
    context = response.context

    assert context["dashboard"]["total_videos"] == 3
    assert context["dashboard"]["completed"] == 1
    assert context["dashboard"]["processing"] == 1
    assert context["dashboard"]["failed"] == 1
    assert context["recent_jobs"][0]["file_name"] == "running.mp4"
    assert context["recent_jobs"][0]["status_class"] == "info"
    assert context["recent_jobs"][1]["status_class"] == "success"
    assert context["recent_jobs"][2]["status_class"] == "danger"
    assert context["system_information"]["cpu_usage"] == "11.0%"
    assert context["system_information"]["memory_usage"] == "52.5%"
    assert context["system_information"]["gpu_usage"] == "7%"
    assert context["system_information"]["disk_usage"] == "39.3%"
