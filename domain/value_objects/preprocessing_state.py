"""
===============================================================================
BHASHA MITRA
Preprocessing State
===============================================================================

Description:
    Represents the persisted state of the preprocessing stages of a
    translation job.

Responsibilities:
    - Track whether audio extraction has completed
    - Store the generated audio file location
    - Track whether ASR has completed
    - Store the generated transcript location

Preprocessing state is independent of TranslationJob lifecycle status.
A job may remain PENDING while preprocessing is completed and waiting for
the user to start translation.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreprocessingState:
    """
    Persisted state of translation-job preprocessing.
    """

    audio_extracted: bool = False

    audio_file: Path | None = None

    asr_completed: bool = False

    transcript_file: Path | None = None

    @property
    def ready_for_translation(self) -> bool:
        """
        Return True when all preprocessing stages are complete.
        """

        return (
            self.audio_extracted
            and self.audio_file is not None
            and self.asr_completed
            and self.transcript_file is not None
        )

    def to_dict(self) -> dict:
        """
        Convert preprocessing state to a serializable dictionary.
        """

        return {
            "audio_extracted": self.audio_extracted,
            "audio_file": (
                str(self.audio_file)
                if self.audio_file
                else None
            ),
            "asr_completed": self.asr_completed,
            "transcript_file": (
                str(self.transcript_file)
                if self.transcript_file
                else None
            ),
        }