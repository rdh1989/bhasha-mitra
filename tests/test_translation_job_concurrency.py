import threading
import time
import unittest
import os
from unittest.mock import patch

from app.jobs import JobManager
from app.models.translate import TranslationEngine


class FakeMemoryPolicy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def can_start_translation_job(self):
        return self.allowed


class TranslationJobConcurrencyTests(unittest.TestCase):
    def make_manager(self, maximum=3, policy=None):
        return JobManager(max_translation_jobs=maximum, memory_policy=policy or FakeMemoryPolicy())

    def wait_for(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.assertTrue(predicate())

    def test_one_two_and_three_jobs_are_admitted(self):
        manager = self.make_manager()
        release = threading.Event()
        started = []

        def work(index):
            started.append(index)
            release.wait(2)

        try:
            for index in range(3):
                manager.submit(work, index)
            self.wait_for(lambda: manager.active_job_count == 3)
            self.assertEqual({0, 1, 2}, set(started))
        finally:
            release.set()
            manager.shutdown()

    def test_fourth_job_is_queued_until_a_slot_completes(self):
        manager = self.make_manager()
        release = threading.Event()
        fourth_started = threading.Event()

        def work(index):
            if index == 3:
                fourth_started.set()
            release.wait(2)

        try:
            for index in range(4):
                manager.submit(work, index)
            self.wait_for(lambda: manager.active_job_count == 3)
            self.assertEqual(1, manager.queued_job_count)
            self.assertFalse(fourth_started.is_set())
            release.set()
            self.wait_for(fourth_started.is_set)
        finally:
            release.set()
            manager.shutdown()

    def test_memory_rejection_queues_and_later_admits(self):
        policy = FakeMemoryPolicy(allowed=False)
        manager = self.make_manager(policy=policy)
        started = threading.Event()
        try:
            manager.submit(lambda: started.set())
            self.wait_for(lambda: manager.queued_job_count == 1)
            self.assertEqual(0, manager.active_job_count)
            self.assertFalse(started.is_set())
            policy.allowed = True
            self.wait_for(started.is_set, timeout=3)
        finally:
            manager.shutdown()

    def test_queued_cancel_removes_job_before_worker_runs(self):
        manager = self.make_manager(maximum=1)
        release = threading.Event()
        second_started = threading.Event()
        try:
            first = manager.create("en", "mr", "first.mp4", "first.mp4")
            second = manager.create("en", "mr", "second.mp4", "second.mp4")

            manager.submit(lambda _job_id: release.wait(2), first.id)
            self.wait_for(lambda: manager.active_job_count == 1)
            manager.submit(lambda _job_id: second_started.set(), second.id)
            self.wait_for(lambda: manager.queued_job_count == 1)

            cancelled = manager.request_cancel(second.id)
            self.assertIsNotNone(cancelled)
            self.assertEqual(cancelled.stage, "cancelled")
            self.assertTrue(cancelled.done)
            self.assertEqual(0, manager.queued_job_count)

            release.set()
            time.sleep(0.05)
            self.assertFalse(second_started.is_set())
        finally:
            release.set()
            manager.shutdown()

    def test_repeated_cancel_requests_are_idempotent_for_running_job(self):
        manager = self.make_manager(maximum=1)
        try:
            job = manager.create("en", "mr", "video.mp4", "video.mp4")
            job.stage = "translating"
            first = manager.request_cancel(job.id)
            second = manager.request_cancel(job.id)

            self.assertIs(first, second)
            self.assertEqual("cancelling", second.stage)
            self.assertFalse(second.done)
        finally:
            manager.shutdown()

    def test_late_completion_update_cannot_overwrite_cancelled_job(self):
        manager = self.make_manager(maximum=1)
        try:
            job = manager.create("en", "mr", "video.mp4", "video.mp4")
            job.stage = "translating"
            manager.request_cancel(job.id)
            manager.update(job.id, stage="completed", done=True, output_path="out.mp4", message="Done!")
            state = manager.get(job.id)

            self.assertEqual("cancelled", state.stage)
            self.assertTrue(state.done)
            self.assertIsNone(state.output_path)
            self.assertEqual("Cancelled.", state.message)
        finally:
            manager.shutdown()

    def test_active_count_never_exceeds_configured_maximum(self):
        manager = self.make_manager(maximum=2)
        release = threading.Event()
        observed = []

        def work():
            observed.append(manager.active_job_count)
            release.wait(2)

        try:
            for _ in range(5):
                manager.submit(work)
            self.wait_for(lambda: manager.active_job_count == 2)
            self.assertLessEqual(max(observed), 2)
        finally:
            release.set()
            manager.shutdown()

    def test_shared_translation_engine_is_not_duplicated(self):
        manager = self.make_manager()
        engine = object()
        seen = []
        done = threading.Event()

        def work(shared_engine):
            seen.append(id(shared_engine))
            if len(seen) == 3:
                done.set()

        try:
            for _ in range(3):
                manager.submit(work, engine)
            self.wait_for(done.is_set)
            self.assertEqual({id(engine)}, set(seen))
        finally:
            manager.shutdown()

    def test_invalid_translation_limit_is_clamped_to_one(self):
        manager = self.make_manager(maximum=1)
        try:
            with self.assertRaises(ValueError):
                JobManager(max_translation_jobs=0, memory_policy=FakeMemoryPolicy())
        finally:
            manager.shutdown()

    def test_translation_engine_unload_waits_for_active_user(self):
        engine = TranslationEngine("test-model")
        engine._model = object()
        with engine._usage_condition:
            engine._active_users = 1

        finished = threading.Event()

        def unload():
            engine.unload()
            finished.set()

        thread = threading.Thread(target=unload)
        thread.start()
        self.assertFalse(finished.wait(0.05))
        self.assertIsNotNone(engine._model)
        with engine._usage_condition:
            engine._active_users = 0
            engine._usage_condition.notify_all()
        thread.join(1)
        self.assertTrue(finished.is_set())
        self.assertIsNone(engine._model)

    def test_translation_limit_is_environment_configurable(self):
        with patch.dict(os.environ, {"MAX_PARALLEL_TRANSLATION_JOBS": "4"}, clear=True):
            import importlib
            import app.config as config

            reloaded = importlib.reload(config)
            self.assertEqual(4, reloaded.MAX_PARALLEL_TRANSLATION_JOBS)


if __name__ == "__main__":
    unittest.main()