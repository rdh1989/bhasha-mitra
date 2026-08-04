"""
===============================================================================
Module: Worker Manager
Project: Bhasha Mitra
Layer: Workers
===============================================================================

Central manager for all background workers.

Responsibilities
----------------
- Register workers
- Start all workers
- Stop all workers
- Retrieve workers
- Report worker status

Acts as the single entry point for managing the worker infrastructure.
"""

from __future__ import annotations

import logging

from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages all background workers.
    """

    def __init__(self) -> None:
        self._workers: dict[str, BaseWorker] = {}

    def register(
        self,
        worker: BaseWorker,
    ) -> None:
        """
        Register a worker.

        Raises:
            ValueError:
                If a worker with the same name already exists.
        """
        if worker.name in self._workers:
            raise ValueError(
                f"Worker '{worker.name}' is already registered."
            )

        self._workers[worker.name] = worker

        logger.info(
            "Registered worker '%s'.",
            worker.name,
        )

    def get(
        self,
        name: str,
    ) -> BaseWorker | None:
        """
        Retrieve a registered worker.
        """
        return self._workers.get(name)

    def start_all(self) -> None:
        """
        Start all registered workers.
        """
        logger.info("Starting all workers.")

        for worker in self._workers.values():
            worker.start()

    def stop_all(self) -> None:
        """
        Stop all registered workers.
        """
        logger.info("Stopping all workers.")

        for worker in self._workers.values():
            worker.stop()

    def join_all(
        self,
        timeout: float | None = None,
    ) -> None:
        """
        Wait for all workers to finish.
        """
        for worker in self._workers.values():
            worker.join(timeout)

    def unregister(
        self,
        name: str,
    ) -> None:
        """
        Remove a worker.

        If the worker is running, it is stopped first.
        """
        worker = self._workers.pop(name, None)

        if worker is None:
            return

        if worker.is_running:
            worker.stop()

        logger.info(
            "Unregistered worker '%s'.",
            name,
        )

    def clear(self) -> None:
        """
        Stop and remove all workers.
        """
        self.stop_all()
        self._workers.clear()

    @property
    def worker_count(self) -> int:
        """
        Number of registered workers.
        """
        return len(self._workers)

    def names(self) -> list[str]:
        """
        Return registered worker names.
        """
        return sorted(self._workers.keys())

    def status(self) -> dict[str, bool]:
        """
        Returns worker running status.

        Example
        -------
        {
            "translation": True,
            "cleanup": False
        }
        """
        return {
            name: worker.is_running
            for name, worker in self._workers.items()
        }