"""
Data Transfer Object for creating a translation job.
"""

from dataclasses import dataclass
from pathlib import Path

from domain.enums.job_priority import JobPriority


@dataclass(slots=True, frozen=True)
class CreateJobRequest:
    """
    Represents an incoming translation request.

    This DTO carries validated user input from the
    Presentation layer into the Application layer.
    """

    input_file: Path

    source_language: str

    target_language: str

    priority: JobPriority = JobPriority.NORMAL