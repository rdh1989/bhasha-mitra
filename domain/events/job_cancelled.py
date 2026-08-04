"""
===============================================================================
Module: Job Cancelled Event
===============================================================================
"""

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobCancelledEvent(BaseEvent):
    """
    Raised whenever a job is cancelled.
    """

    job_id: str