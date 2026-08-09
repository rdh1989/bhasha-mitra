"""
===============================================================================
BHASHA MITRA
Worker Registry
===============================================================================

Description:
    Creates and wires application workers with their required dependencies.

Responsibilities:
    - Create worker instances
    - Inject shared dependencies
    - Register workers with WorkerManager

Business logic must not be implemented here.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

from workers.job_queue import JobQueue
from workers.translation_worker import TranslationWorker
from workers.cleanup_worker import CleanupWorker
from workers.retry_worker import RetryWorker
from workers.monitoring_worker import MonitoringWorker
from workers.worker_manager import WorkerManager

from app.application.interfaces.job_repository import JobRepository

from infrastructure.filesystem.path_manager import PathManager
from infrastructure.media.audio_extractor import AudioExtractor


def register_workers(
    manager: WorkerManager,
    job_queue: JobQueue[str],
    job_repository: JobRepository,
    path_manager: PathManager,
) -> None:
    """
    Create and register all application workers.

    Args:
        manager:
            Worker manager.

        job_queue:
            Shared application job queue.

        job_repository:
            Translation job repository.

        path_manager:
            Centralized storage path manager.
    """

    audio_extractor = AudioExtractor()

    workers = (
        TranslationWorker(
            job_queue=job_queue,
            job_repository=job_repository,
            path_manager=path_manager,
            audio_extractor=audio_extractor,
        ),
        CleanupWorker(),
        RetryWorker(job_queue),
        MonitoringWorker(),
    )

    for worker in workers:
        manager.register(worker)