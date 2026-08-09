"""
===============================================================================
BHASHA MITRA
Translation Job Domain Entity
===============================================================================

Module:
    translation_job.py

Layer:
    Domain

Description:
    Aggregate root representing a translation job.

Responsibilities:
    - Own the complete job lifecycle
    - Validate state transitions
    - Track progress
    - Track preprocessing state
    - Track timestamps
    - Maintain domain events
    - Maintain business invariants
    - Support persistence reconstruction

Logging:
    Persistence reconstruction is logged at debug level.
    Business/operational lifecycle logging is handled by the
    application and worker layers.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import logging

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
from domain.value_objects.preprocessing_state import (
    PreprocessingState,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TranslationJob:
    """
    Aggregate Root representing one translation request.
    """

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    input_file: Path

    source_language: str | None = None

    target_language: str | None = None

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
    # Preprocessing
    # ------------------------------------------------------------------

    preprocessing: PreprocessingState = field(
        default_factory=PreprocessingState
    )

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

        Existing preprocessing artifacts are retained because they can
        be safely reused by the retry.
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
    # Preprocessing
    # ------------------------------------------------------------------

    def mark_audio_extracted(
        self,
        audio_file: Path,
    ) -> None:
        """
        Record successful audio extraction.
        """

        self.preprocessing = PreprocessingState(
            audio_extracted=True,
            audio_file=audio_file,
            asr_completed=self.preprocessing.asr_completed,
            transcript_file=self.preprocessing.transcript_file,
        )

        self.updated_at = datetime.now(UTC)

    def mark_asr_completed(
        self,
        transcript_file: Path,
    ) -> None:
        """
        Record successful ASR processing.
        """

        if not self.preprocessing.audio_extracted:
            raise InvalidJobStateError(
                "ASR cannot be marked complete before audio extraction."
            )

        self.preprocessing = PreprocessingState(
            audio_extracted=True,
            audio_file=self.preprocessing.audio_file,
            asr_completed=True,
            transcript_file=transcript_file,
        )

        self.updated_at = datetime.now(UTC)

    @property
    def preprocessing_ready(self) -> bool:
        """
        Return True when audio extraction and ASR are complete.
        """

        return self.preprocessing.ready_for_translation

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

        end_time = (
            self.completed_at
            or datetime.now(UTC)
        )

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

            "preprocessing": self.preprocessing.to_dict(),

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

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "TranslationJob":
        """
        Reconstruct a TranslationJob from persisted data.

        Loading an existing job must not create a new
        JobCreatedEvent.
        """

        progress_data = data["progress"]

        preprocessing_data = data.get(
            "preprocessing",
            {},
        )

        preprocessing = PreprocessingState(
            audio_extracted=preprocessing_data.get(
                "audio_extracted",
                False,
            ),
            audio_file=(
                Path(
                    preprocessing_data["audio_file"]
                )
                if preprocessing_data.get(
                    "audio_file"
                )
                else None
            ),
            asr_completed=preprocessing_data.get(
                "asr_completed",
                False,
            ),
            transcript_file=(
                Path(
                    preprocessing_data[
                        "transcript_file"
                    ]
                )
                if preprocessing_data.get(
                    "transcript_file"
                )
                else None
            ),
        )

        job = cls(
            input_file=Path(
                data["input_file"]
            ),
            source_language=data.get(
                "source_language"
            ),
            target_language=data.get(
                "target_language"
            ),
            id=data["id"],
            priority=JobPriority[
                data["priority"]
            ],
            status=JobStatus(
                data["status"]
            ),
            progress=JobProgress(
                stage=progress_data["stage"],
                percentage=progress_data[
                    "percentage"
                ],
                message=progress_data.get(
                    "message",
                    "",
                ),
            ),
            retry_count=data.get(
                "retry_count",
                0,
            ),
            output_file=(
                Path(data["output_file"])
                if data.get("output_file")
                else None
            ),
            error_message=data.get(
                "error_message"
            ),
            preprocessing=preprocessing,
            created_at=datetime.fromisoformat(
                data["created_at"]
            ),
            started_at=(
                datetime.fromisoformat(
                    data["started_at"]
                )
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(
                    data["completed_at"]
                )
                if data.get("completed_at")
                else None
            ),
            cancelled_at=(
                datetime.fromisoformat(
                    data["cancelled_at"]
                )
                if data.get("cancelled_at")
                else None
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"]
            ),
        )

        # Rehydrating an existing entity must not
        # emit a new creation event.
        job.clear_events()

        logger.debug(
            "Translation job rehydrated | "
            "job_id=%s status=%s",
            job.id,
            job.status.value,
        )

        return job

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