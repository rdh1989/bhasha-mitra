"""
===============================================================================
Module: Base Worker
Project: Bhasha Mitra
Layer: Workers
===============================================================================

Base class for all background workers.

Responsibilities
----------------
- Worker lifecycle management
- Start/Stop worker
- Worker state
- Logging

Derived workers should implement the `run()` method.

Examples
--------
- TranslationWorker
- CleanupWorker
- RetryWorker
- MonitoringWorker
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
import threading


logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Base class for all background workers.
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def name(self) -> str:
        """
        Worker name.
        """
        return self._name

    @property
    def is_running(self) -> bool:
        """
        Returns True if the worker is running.
        """
        return self._running

    def start(self) -> None:
        """
        Start the worker.

        Does nothing if already running.
        """
        if self._running:
            logger.warning(
                "Worker '%s' is already running.",
                self._name,
            )
            return

        logger.info(
            "Starting worker '%s'.",
            self._name,
        )

        self._running = True

        self._thread = threading.Thread(
            target=self.run,
            name=self._name,
            daemon=True,
        )

        self._thread.start()

    def stop(self) -> None:
        """
        Stop the worker.
        """
        if not self._running:
            return

        logger.info(
            "Stopping worker '%s'.",
            self._name,
        )

        self._running = False

    def join(
        self,
        timeout: float | None = None,
    ) -> None:
        """
        Wait until the worker finishes.
        """
        if self._thread is not None:
            self._thread.join(timeout)

    @abstractmethod
    def run(self) -> None:
        """
        Worker execution loop.

        Must be implemented by derived classes.
        """
        raise NotImplementedError