"""
Domain event raised whenever a new TranslationJob is created.

This event can be consumed by:

- Audit logging
- Worker scheduler
- Notification system
- Telemetry
- Event bus
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class JobCreatedEvent(BaseEvent):
    """
    Raised immediately after a TranslationJob is created.
    """

    job_id: str