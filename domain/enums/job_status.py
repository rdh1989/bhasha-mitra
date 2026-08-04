"""
===============================================================================
Module: Job Status Enumeration
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Defines all valid lifecycle states for a Translation Job.

This enumeration is the single source of truth for job status across the
entire application.

Usage:
    from domain.enums.job_status import JobStatus

    job.status = JobStatus.PENDING
"""

from enum import Enum


class JobStatus(str, Enum):
    """
    Represents the lifecycle state of a translation job.
    """

    PENDING = "PENDING"
    """
    Job has been created but not yet queued.
    """

    QUEUED = "QUEUED"
    """
    Waiting for an available worker.
    """

    RUNNING = "RUNNING"
    """
    Translation is currently in progress.
    """

    COMPLETED = "COMPLETED"
    """
    Translation finished successfully.
    """

    FAILED = "FAILED"
    """
    Translation failed due to an unrecoverable error.
    """

    CANCELLED = "CANCELLED"
    """
    Job was cancelled by the user.
    """

    RETRYING = "RETRYING"
    """
    Worker is retrying a previously failed job.
    """

    PAUSED = "PAUSED"
    """
    Reserved for future support.
    """

    @property
    def is_terminal(self) -> bool:
        """
        Returns True if this status represents the end of the lifecycle.
        """
        return self in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    @property
    def is_active(self) -> bool:
        """
        Returns True while the job is actively progressing.
        """
        return self in {
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.RETRYING,
        }

    @property
    def can_retry(self) -> bool:
        """
        Indicates whether the job can be retried.
        """
        return self == JobStatus.FAILED

    @property
    def can_cancel(self) -> bool:
        """
        Indicates whether the job may still be cancelled.
        """
        return self in {
            JobStatus.PENDING,
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.RETRYING,
        }

    def __str__(self) -> str:
        return self.value