"""
===============================================================================
Module: Job Created Event
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Domain event raised whenever a new TranslationJob is created.

This event can be consumed by:

- Audit logging
- Worker scheduler
- Notification system
- Telemetry
- Event bus
"""

"""
===============================================================================
Module: Job Created Event
===============================================================================
"""

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobCreatedEvent(BaseEvent):
    """
    Raised immediately after a TranslationJob is created.
    """

    job_id: str