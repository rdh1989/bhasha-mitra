"""
===============================================================================
Module: Job Priority Enumeration
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Defines the execution priority of translation jobs.

Priority determines the order in which queued jobs are picked by workers.

Usage:
    from domain.enums.job_priority import JobPriority

    job.priority = JobPriority.NORMAL
"""

from enum import IntEnum


class JobPriority(IntEnum):
    """
    Represents the priority assigned to a translation job.

    Higher numeric values indicate higher priority.
    """

    LOW = 1
    """
    Lowest execution priority.
    Suitable for background or batch processing.
    """

    NORMAL = 2
    """
    Default priority for standard translation requests.
    """

    HIGH = 3
    """
    High priority for time-sensitive translations.
    """

    CRITICAL = 4
    """
    Highest priority.
    Reserved for system or administrator requests.
    """

    @property
    def is_high_priority(self) -> bool:
        """
        Returns True if the job should be processed before normal jobs.
        """
        return self in (
            JobPriority.HIGH,
            JobPriority.CRITICAL,
        )

    @property
    def queue_weight(self) -> int:
        """
        Returns the scheduling weight.

        Higher values are processed first.
        """
        return int(self)

    def __str__(self) -> str:
        return self.name