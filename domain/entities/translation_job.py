"""
===============================================================================
Module: Translation Job
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Represents a translation request.

This is the Aggregate Root of the Job Management domain.

Responsibilities
----------------
• Own the complete job lifecycle
• Validate state transitions
• Track progress
• Track timestamps
• Raise domain events
• Maintain business invariants
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from domain.enums.job_priority import JobPriority
from domain.enums.job_status import JobStatus

from domain.events import (
    BaseEvent,
    JobCancelledEvent,
    JobCompletedEvent,
    JobCreatedEvent,
    JobFailedEvent,
    JobStartedEvent,
)

from domain.exceptions import (
    InvalidJobStateError,
    JobCancelNotAllowedError,
    JobRetryNotAllowedError,
)

from domain.value_objects.job_progress import JobProgress


@dataclass(slots=True)
class TranslationJob:
    """
    Aggregate Root representing one translation request.
    """

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    input_file: Path

    source_language: str

    target_language: str

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    priority: JobPriority = JobPriority.NORMAL

    status: JobStatus = JobStatus.PENDING

    progress: JobProgress = field(
        default_factory=JobProgress.not_started
    )

    retry_count: int = 0

    output_file: Path | None = None

    error_message: str | None = None

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None

    cancelled_at: datetime | None = None

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    # ------------------------------------------------------------------
    # Domain Events
    # ------------------------------------------------------------------

    _events: list[BaseEvent] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """
        Raise initial creation event.
        """

        self._events.append(
            JobCreatedEvent(
                job_id=self.id
            )
        )


    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def queue(self) -> None:
        """
        Move the job to the queued state.
        """
        self._transition_to(
            JobStatus.QUEUED,
            allowed_from={
                JobStatus.PENDING,
                JobStatus.RETRYING,
            },
        )

    def start(self) -> None:
        """
        Start processing the job.
        """
        self._transition_to(
            JobStatus.RUNNING,
            allowed_from={
                JobStatus.QUEUED,
            },
        )

        self.started_at = datetime.now(UTC)

        self._events.append(
            JobStartedEvent(
                job_id=self.id,
            )
        )

    def complete(
        self,
        output_file: Path,
    ) -> None:
        """
        Mark the job as completed.
        """
        self.output_file = output_file

        self.completed_at = datetime.now(UTC)

        self.progress = JobProgress.completed_progress()

        self._transition_to(
            JobStatus.COMPLETED,
            allowed_from={
                JobStatus.RUNNING,
            },
        )

        self._events.append(
            JobCompletedEvent(
                job_id=self.id,
                output_file=str(output_file),
            )
        )

    def fail(
        self,
        error_message: str,
    ) -> None:
        """
        Mark the job as failed.
        """
        self.error_message = error_message

        self.completed_at = datetime.now(UTC)

        self._transition_to(
            JobStatus.FAILED,
            allowed_from={
                JobStatus.RUNNING,
            },
        )

        self._events.append(
            JobFailedEvent(
                job_id=self.id,
                error_message=error_message,
            )
        )

    def cancel(self) -> None:
        """
        Cancel the job.
        """
        if not self.status.can_cancel:
            raise JobCancelNotAllowedError(
                f"Job '{self.id}' cannot be cancelled while in "
                f"'{self.status}'."
            )

        self.cancelled_at = datetime.now(UTC)

        self._transition_to(
            JobStatus.CANCELLED,
            allowed_from={
                JobStatus.PENDING,
                JobStatus.QUEUED,
                JobStatus.RUNNING,
                JobStatus.RETRYING,
            },
        )

        self._events.append(
            JobCancelledEvent(
                job_id=self.id,
            )
        )

    def retry(self) -> None:
        """
        Retry a failed translation job.
        """
        if not self.status.can_retry:
            raise JobRetryNotAllowedError(
                f"Job '{self.id}' cannot be retried while in "
                f"'{self.status}'."
            )

        self.retry_count += 1

        self.error_message = None

        self.started_at = None

        self.completed_at = None

        self.cancelled_at = None

        self.output_file = None

        self.progress = JobProgress.not_started()

        self._transition_to(
            JobStatus.RETRYING,
            allowed_from={
                JobStatus.FAILED,
            },
        )

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def update_progress(
        self,
        stage: str,
        percentage: int,
        message: str = "",
    ) -> None:
        """
        Update the current execution progress.
        """
        if self.status != JobStatus.RUNNING:
            raise InvalidJobStateError(
                "Progress can only be updated while the job is running."
            )

        self.progress = JobProgress(
            stage=stage,
            percentage=percentage,
            message=message,
        )

        self.updated_at = datetime.now(UTC)


    # ------------------------------------------------------------------
    # State Transition
    # ------------------------------------------------------------------

    def _transition_to(
        self,
        new_status: JobStatus,
        *,
        allowed_from: set[JobStatus],
    ) -> None:
        """
        Validate and perform a state transition.
        """

        if self.status not in allowed_from:
            raise InvalidJobStateError(
                f"Cannot transition from "
                f"'{self.status}' to '{new_status}'."
            )

        self.status = new_status
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Domain Events
    # ------------------------------------------------------------------

    @property
    def events(self) -> tuple[BaseEvent, ...]:
        """
        Returns all pending domain events as a read-only tuple.
        """
        return tuple(self._events)

    def pull_events(self) -> list[BaseEvent]:
        """
        Returns all pending domain events and clears the internal queue.

        The Application layer should call this after persisting the job.
        """

        events = self._events.copy()
        self._events.clear()

        return events

    def clear_events(self) -> None:
        """
        Clears all pending events.
        """
        self._events.clear()

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        return self.status == JobStatus.PENDING

    @property
    def is_queued(self) -> bool:
        return self.status == JobStatus.QUEUED

    @property
    def is_running(self) -> bool:
        return self.status == JobStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        return self.status == JobStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self.status == JobStatus.CANCELLED

    @property
    def is_finished(self) -> bool:
        """
        True when no more processing can occur.
        """
        return self.status.is_terminal

    @property
    def duration_seconds(self) -> float | None:
        """
        Returns the execution duration in seconds.

        Returns:
            None if the job has never started.
        """

        if self.started_at is None:
            return None

        end_time = self.completed_at or datetime.now(UTC)

        return (
            end_time - self.started_at
        ).total_seconds()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert the entity into a serializable dictionary.
        """

        return {

            "id": self.id,

            "status": self.status.value,

            "priority": self.priority.name,

            "source_language": self.source_language,

            "target_language": self.target_language,

            "input_file": str(self.input_file),

            "output_file": (
                str(self.output_file)
                if self.output_file
                else None
            ),

            "retry_count": self.retry_count,

            "progress": self.progress.to_dict(),

            "error_message": self.error_message,

            "created_at": self.created_at.isoformat(),

            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),

            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),

            "cancelled_at": (
                self.cancelled_at.isoformat()
                if self.cancelled_at
                else None
            ),

            "updated_at": self.updated_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "TranslationJob("
            f"id='{self.id}', "
            f"status='{self.status.value}', "
            f"progress={self.progress.percentage}%, "
            f"source='{self.source_language}', "
            f"target='{self.target_language}'"
            ")"
        )