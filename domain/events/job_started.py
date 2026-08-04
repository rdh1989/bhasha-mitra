"""
===============================================================================
Module: Job Started Event
===============================================================================
"""

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobStartedEvent(BaseEvent):
    """
    Raised when processing begins.
    """

    job_id: str