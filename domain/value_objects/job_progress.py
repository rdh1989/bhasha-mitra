"""
===============================================================================
Module: Job Progress Value Object
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Represents the current execution progress of a translation job.

A JobProgress object is immutable from the domain perspective and is used to
track the current processing stage, completion percentage, and status message.

Typical Pipeline

Upload
 ↓
Pre-processing
 ↓
Speech Recognition (ASR)
 ↓
Language Detection
 ↓
Translation
 ↓
Subtitle Generation
 ↓
Text-To-Speech
 ↓
Export
 ↓
Completed
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobProgress:
    """
    Represents the current progress of a translation job.
    """

    stage: str
    percentage: int
    message: str = ""

    def __post_init__(self) -> None:
        """
        Validate progress values.
        """
        if not 0 <= self.percentage <= 100:
            raise ValueError(
                "Job progress percentage must be between 0 and 100."
            )

    @property
    def completed(self) -> bool:
        """
        Returns True when the job reaches 100%.
        """
        return self.percentage == 100

    @property
    def started(self) -> bool:
        """
        Returns True once processing has started.
        """
        return self.percentage > 0

    @property
    def remaining(self) -> int:
        """
        Returns remaining percentage.
        """
        return 100 - self.percentage

    def to_dict(self) -> dict:
        """
        Convert to serializable dictionary.
        """
        return {
            "stage": self.stage,
            "percentage": self.percentage,
            "message": self.message,
        }

    @classmethod
    def not_started(cls) -> "JobProgress":
        """
        Initial progress.
        """
        return cls(
            stage="Pending",
            percentage=0,
            message="Waiting for worker.",
        )

    @classmethod
    def completed_progress(cls) -> "JobProgress":
        """
        Completed progress.
        """
        return cls(
            stage="Completed",
            percentage=100,
            message="Translation completed successfully.",
        )

    def __str__(self) -> str:
        return (
            f"{self.stage} "
            f"({self.percentage}%)"
        )