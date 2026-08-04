"""
===============================================================================
Module: Job Completed Event
===============================================================================
"""

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobCompletedEvent(BaseEvent):
    """
    Raised after successful completion.
    """

    job_id: str

    output_file: str