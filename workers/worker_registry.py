"""
===============================================================================
Module: Worker Registry
Project: Bhasha Mitra
Layer: Workers
===============================================================================

Registers and wires all application workers.

Responsibilities
----------------
- Create worker instances
- Inject shared dependencies
- Register workers with WorkerManager

This file serves as the composition root for the worker infrastructure.
Business logic should never live here.
"""

from __future__ import annotations

from workers.job_queue import JobQueue
from workers.translation_worker import TranslationWorker
from workers.cleanup_worker import CleanupWorker
from workers.retry_worker import RetryWorker
from workers.monitoring_worker import MonitoringWorker
from workers.worker_manager import WorkerManager


def register_workers(
    manager: WorkerManager,
    job_queue: JobQueue[str],
) -> None:
    """
    Create and register all application workers.

    Args:
        manager:
            Worker manager.

        job_queue:
            Shared application job queue.
    """

    workers = (
        TranslationWorker(job_queue),
        CleanupWorker(),
        RetryWorker(job_queue),
        MonitoringWorker(),
    )

    for worker in workers:
        manager.register(worker)