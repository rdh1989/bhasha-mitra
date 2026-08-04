"""
===============================================================================
Module: Scheduler
Project: Bhasha Mitra
Layer: Workers
===============================================================================

Background scheduler infrastructure.

Responsibilities
----------------
- Execute scheduled tasks
- Run maintenance jobs
- Trigger periodic workers
- Manage scheduler lifecycle

This is intentionally a lightweight scheduler for the MVP.
Future implementations may replace it with APScheduler,
Celery Beat, Windows Task Scheduler, or another scheduler.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Lightweight background scheduler.
    """

    def __init__(self) -> None:
        self._tasks: list[tuple[Callable[[], None], int]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def register(
        self,
        task: Callable[[], None],
        interval_seconds: int,
    ) -> None:
        """
        Register a scheduled task.

        Args:
            task:
                Function to execute.

            interval_seconds:
                Execution interval.
        """
        self._tasks.append(
            (
                task,
                interval_seconds,
            )
        )

        logger.info(
            "Registered scheduled task '%s' (%ss).",
            task.__name__,
            interval_seconds,
        )

    def start(self) -> None:
        """
        Start the scheduler.
        """
        if self._running:
            logger.warning("Scheduler already running.")
            return

        logger.info("Starting scheduler.")

        self._running = True

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="Scheduler",
        )

        self._thread.start()

    def stop(self) -> None:
        """
        Stop the scheduler.
        """
        if not self._running:
            return

        logger.info("Stopping scheduler.")

        self._running = False

    def join(
        self,
        timeout: float | None = None,
    ) -> None:
        """
        Wait until scheduler exits.
        """
        if self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        """
        Scheduler execution loop.
        """
        next_run: dict[Callable[[], None], float] = {}

        while self._running:

            now = time.time()

            for task, interval in self._tasks:

                scheduled = next_run.get(task, 0)

                if now >= scheduled:

                    try:
                        task()

                    except Exception:

                        logger.exception(
                            "Scheduled task '%s' failed.",
                            task.__name__,
                        )

                    next_run[task] = now + interval

            time.sleep(1)

    @property
    def is_running(self) -> bool:
        """
        Returns scheduler state.
        """
        return self._running

    @property
    def task_count(self) -> int:
        """
        Returns number of registered tasks.
        """
        return len(self._tasks)