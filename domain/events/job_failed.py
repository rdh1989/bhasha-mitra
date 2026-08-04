"""
===============================================================================
Module: Job Failed Event
===============================================================================
"""

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobFailedEvent(BaseEvent):
    """
    Raised whenever processing fails.
    """

    job_id: str

    error_message: str