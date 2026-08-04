"""
===============================================================================
Module: Base Domain Event
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Base class for all domain events.

Every domain event inherits from this class to provide common metadata.

Responsibilities:
    • Unique event identifier
    • Event timestamp
    • Event name
    • Serialization support

Examples:
    JobCreatedEvent
    JobStartedEvent
    JobCompletedEvent
    JobFailedEvent
    JobCancelledEvent
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BaseEvent:
    """
    Base class for all domain events.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))

    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    @property
    def event_name(self) -> str:
        """
        Returns the event class name.
        """
        return self.__class__.__name__

    def to_dict(self) -> dict:
        """
        Convert event into a serializable dictionary.
        """
        data = asdict(self)

        data["event_name"] = self.event_name
        data["occurred_at"] = self.occurred_at.isoformat()

        return data

    def __str__(self) -> str:
        return f"{self.event_name}({self.event_id})"