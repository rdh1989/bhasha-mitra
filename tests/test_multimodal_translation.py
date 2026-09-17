import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.config import ALLOWED_AUDIO_EXTENSIONS
from app.fs_browse import list_directory
from app.jobs import JobManager, JobState
from app.models.asr import Segment, TranscriptionResult
from app.pipeline import run_audio_pipeline, run_text_pipeline


class FakeJobs:
    def __init__(self):
        self.updates = []

    def raise_if_cancelled(self, _job_id):
        return None

    def update(self, _job_id, **kwargs):
        self.updates.append(kwargs)

    def mark_cancelled(self, _job_id):
        self.updates.append({"stage": "cancelled"})


class MultimediaTranslationTests(unittest.TestCase):
    def test_audio_extensions_and_browser_filter(self):
        self.assertEqual(
            ALLOWED_AUDIO_EXTENSIONS,
            {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for suffix in ALLOWED_AUDIO_EXTENSIONS:
                (root / f"audio{suffix.upper()}").touch()
            (root / "video.mp4").touch()
            (root / "notes.txt").touch()
            audio_names = {entry["name"] for entry in list_directory(directory, "audio")["entries"]}
            video_names = {entry["name"] for entry in list_directory(directory, "video")["entries"]}
        self.assertEqual(audio_names, {f"audio{suffix.upper()}" for suffix in ALLOWED_AUDIO_EXTENSIONS})
        self.assertEqual(video_names, {"video.mp4"})

    def test_audio_pipeline_sets_wav_output(self):
        jobs = FakeJobs()
        transcript = TranscriptionResult([Segment(0.0, 1.0, "hello")], "en", 0.9)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.mp3"
            source.touch()
            output = Path(directory) / "dubbed_audio.wav"
            with patch("app.pipeline.OUTPUTS_DIR", Path(directory)), \
                 patch("app.pipeline.extract_audio"), \
                 patch("app.pipeline._translate", return_value=[(0.0, 1.0, "translated")]), \
                 patch("app.pipeline._synthesize_and_align", return_value=output):
                run_audio_pipeline(
                    "job", str(source), "en", "hi", jobs,
                    SimpleNamespace(transcribe=lambda *_args, **_kwargs: transcript),
                    object(), object(), object(), object(),
                )
        self.assertEqual(jobs.updates[-1]["output_path"], str(output))
        self.assertTrue(jobs.updates[-1]["output_path"].endswith("dubbed_audio.wav"))

    def test_audio_job_creation_and_text_validation(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.wav"
            source.touch()
            fake_manager = SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(id="audio-job", **kwargs),
                update=lambda *_args, **_kwargs: None,
                submit=lambda *_args, **_kwargs: None,
            )
            with patch.object(main, "job_manager", fake_manager):
                response = main.create_audio_jobs(request, main.CreateAudioJobsRequest(
                    audio_paths=[str(source)], source_lang="en", target_lang="hi"
                ))
        self.assertEqual(response, {"job_ids": ["audio-job"]})
        with self.assertRaises(Exception):
            main.translate_text_request(request, main.TranslateTextRequest(text="   ", source_lang="en", target_lang="hi"))
        with patch.object(main, "translate_text", return_value="translated"):
            self.assertEqual(
                main.translate_text_request(request, main.TranslateTextRequest(
                    text="source", source_lang="en", target_lang="hi"
                )),
                {"translated_text": "translated"},
            )
        with tempfile.TemporaryDirectory() as directory:
            unsupported = Path(directory) / "input.txt"
            unsupported.touch()
            with self.assertRaises(Exception):
                main.create_audio_jobs(request, main.CreateAudioJobsRequest(
                    audio_paths=[str(unsupported)], source_lang="en", target_lang="hi"
                ))

    def test_text_file_browse_and_translation_validation(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_file = root / "source.txt"
            text_file.write_text("source text", encoding="utf-8")
            (root / "source.csv").touch()
            names = {entry["name"] for entry in list_directory(directory, "text")["entries"]}
            self.assertEqual(names, {"source.txt"})
            with patch.object(main, "translate_text", return_value="translated") as translate:
                response = main.translate_text_request(request, main.TranslateTextRequest(
                    text_path=str(text_file), source_lang="en", target_lang="hi"
                ))
            self.assertEqual(response, {"translated_text": "translated"})
            self.assertEqual(translate.call_args.args[0], "source text")
            with self.assertRaises(Exception):
                main.translate_text_request(request, main.TranslateTextRequest(
                    text_path=str(root / "source.csv"), source_lang="en", target_lang="hi"
                ))

    def test_text_job_persists_typed_input_and_submits_to_text_slot(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        submitted = []
        fake_manager = SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(id="text-job", **kwargs),
            update=lambda *_args, **kwargs: updates.append(kwargs),
            submit_text=lambda function, *args: submitted.append((function, args)),
        )
        updates = []
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(main, "OUTPUTS_DIR", Path(directory)), \
             patch.object(main, "job_manager", fake_manager):
            response = main.create_text_job(request, main.CreateTextJobRequest(
                text="exact typed text", source_lang="en", target_lang="hi"
            ))
            input_path = Path(directory) / "typed-text" / "text-job" / "input.txt"
            self.assertEqual(input_path.read_text(encoding="utf-8"), "exact typed text")
        self.assertEqual(response, {"job_id": "text-job"})
        self.assertEqual(submitted[0][0], main.run_text_pipeline)
        self.assertTrue(any(item.get("source_path", "").endswith("input.txt") for item in updates))

    def test_text_job_uses_txt_source_and_pipeline_writes_text_output(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        updates = []
        submitted = []
        fake_manager = SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(id="text-job", **kwargs),
            update=lambda *_args, **kwargs: updates.append(kwargs),
            submit_text=lambda function, *args: submitted.append((function, args)),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("source", encoding="utf-8")
            with patch.object(main, "job_manager", fake_manager):
                response = main.create_text_job(request, main.CreateTextJobRequest(
                    text_path=str(source), source_lang="en", target_lang="hi"
                ))
            self.assertEqual(response, {"job_id": "text-job"})
            self.assertEqual(submitted[0][1][1], str(source))
            jobs = FakeJobs()
            with patch("app.pipeline.OUTPUTS_DIR", Path(directory)), \
                 patch("app.pipeline._translate", return_value=[(0.0, 1.0, "translated")]) as translate:
                run_text_pipeline("result-job", str(source), "en", "hi", jobs, object(), object(), object())
            output = Path(jobs.updates[-1]["output_path"])
            self.assertEqual(output.suffix, ".txt")
            self.assertEqual(output.read_text(encoding="utf-8"), "translated")
            self.assertEqual(translate.call_count, 1)

    def test_reserved_text_slot_admits_after_three_media_workers(self):
        class PermissiveMemory:
            def can_start_translation_job(self):
                return True

        manager = JobManager(max_translation_jobs=3, memory_policy=PermissiveMemory())
        release = __import__("threading").Event()
        text_started = __import__("threading").Event()
        second_text_started = __import__("threading").Event()
        try:
            for _ in range(3):
                manager.submit(lambda: release.wait(2))
            manager.submit_text(lambda: (text_started.set(), release.wait(2)))
            deadline = __import__("time").monotonic() + 2
            while __import__("time").monotonic() < deadline and not text_started.is_set():
                __import__("time").sleep(0.01)
            self.assertEqual(manager.active_job_count, 3)
            self.assertEqual(manager.active_text_job_count, 1)
            self.assertTrue(text_started.is_set())
            manager.submit_text(lambda: second_text_started.set())
            __import__("time").sleep(0.05)
            self.assertFalse(second_text_started.is_set())
        finally:
            release.set()
            manager.shutdown()

    def test_text_retry_uses_reserved_text_slot(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        job = SimpleNamespace(id="text-job", source_lang="en", target_lang="hi", message="Retry queued")
        submitted = []
        manager = SimpleNamespace(
            retry=lambda _job_id: job,
            submit_text=lambda function, *args: submitted.append((function, args)),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("source", encoding="utf-8")
            with patch.object(main.db, "get_job_row", return_value={"stage": "failed", "source_path": str(source)}), \
                 patch.object(main, "job_manager", manager):
                main.retry_job(request, "text-job")
        self.assertEqual(submitted[0][0], main.run_text_pipeline)

    def test_output_response_uses_persisted_suffix(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        with tempfile.TemporaryDirectory() as directory:
            for filename, media_type in (("output.mp4", "video/mp4"), ("dubbed_audio.wav", "audio/wav"), ("translated.txt", "text/plain")):
                output = Path(directory) / filename
                output.touch()
                with patch.object(main.job_manager, "get", return_value=SimpleNamespace(
                    output_path=str(output), filename="input.mp4"
                )):
                    response = main.get_output(request, "job")
                self.assertEqual(response.media_type, media_type)

    def test_media_jobs_have_independent_ids_and_cancellation(self):
        manager = JobManager(max_translation_jobs=2)
        video = JobState(id="video", source_lang="en", target_lang="hi", filename="video.mp4")
        audio = JobState(id="audio", source_lang="en", target_lang="hi", filename="audio.wav")
        second_video = JobState(id="second-video", source_lang="en", target_lang="hi", filename="second.mp4")
        second_audio = JobState(id="second-audio", source_lang="en", target_lang="hi", filename="second.wav")
        try:
            with patch("app.jobs.db.update_job_row"):
                manager._jobs = {
                    video.id: video, audio.id: audio,
                    second_video.id: second_video, second_audio.id: second_audio,
                }
                self.assertIs(manager.request_cancel("audio"), audio)
                self.assertIs(manager.request_cancel("second-video"), second_video)
            self.assertTrue(audio.cancel_requested)
            self.assertFalse(video.cancel_requested)
            self.assertTrue(second_video.cancel_requested)
            self.assertFalse(second_audio.cancel_requested)
            self.assertEqual({manager.get("video").id, manager.get("audio").id}, {"video", "audio"})
        finally:
            manager.shutdown()

    def test_audio_retry_uses_audio_runner_and_text_is_not_queued(self):
        from app import main

        request = SimpleNamespace(session={"user": "operator", "role": "operator"})
        row = {"stage": "failed", "source_path": "C:/input.wav"}
        job = SimpleNamespace(id="audio-job", source_lang="en", target_lang="hi", message="Retry queued")
        submitted = []
        fake_manager = SimpleNamespace(
            retry=lambda _job_id: job,
            submit=lambda function, *_args: submitted.append(function),
            active_job_count=1,
        )
        with patch.object(main.db, "get_job_row", return_value=row), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(main, "job_manager", fake_manager):
            main.retry_job(request, "audio-job")
        self.assertEqual(submitted, [main.run_audio_pipeline])
        with patch.object(main, "translate_text", return_value="translated") as translate:
            response = main.translate_text_request(request, main.TranslateTextRequest(
                text="source", source_lang="en", target_lang="hi"
            ))
        self.assertEqual(response, {"translated_text": "translated"})
        translate.assert_called_once()


if __name__ == "__main__":
    unittest.main()