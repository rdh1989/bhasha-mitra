"""
===============================================================================
Module: Job Queue
Project: Bhasha Mitra
Layer: Workers
===============================================================================

Thread-safe in-memory job queue.

Responsibilities
----------------
- Queue jobs
- Retrieve jobs
- Track queue size
- Clear queue

This implementation is intentionally in-memory and can later be replaced
with SQLite, Redis, RabbitMQ, or another queue backend without changing
worker implementations.
"""

from __future__ import annotations

from queue import Empty, Queue
from typing import Generic, TypeVar

T = TypeVar("T")


class JobQueue(Generic[T]):
    """
    Thread-safe FIFO job queue.
    """

    def __init__(
        self,
        max_size: int = 0,
    ) -> None:
        """
        Create a queue.

        Args:
            max_size:
                Maximum number of queued items.
                0 = unlimited.
        """
        self._queue: Queue[T] = Queue(maxsize=max_size)

    def put(
        self,
        job: T,
    ) -> None:
        """
        Add a job to the queue.
        """
        self._queue.put(job)

    def get(
        self,
        timeout: float | None = None,
    ) -> T | None:
        """
        Retrieve the next job.

        Returns None if timeout expires.
        """
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def task_done(self) -> None:
        """
        Mark a job as completed.
        """
        self._queue.task_done()

    def join(self) -> None:
        """
        Block until all queued jobs have been processed.
        """
        self._queue.join()

    def clear(self) -> None:
        """
        Remove all pending jobs.

        Intended for testing or controlled shutdown.
        """
        while not self.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Empty:
                break

    def empty(self) -> bool:
        """
        Returns True when the queue has no jobs.
        """
        return self._queue.empty()

    def size(self) -> int:
        """
        Returns the current queue size.
        """
        return self._queue.qsize()

    def __len__(self) -> int:
        """
        Number of queued jobs.
        """
        return self.size()