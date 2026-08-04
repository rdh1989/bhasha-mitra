"""
Storage Service Contract.

Provides an abstraction for all file storage operations used by
Bhasha Mitra.

The Application layer should never directly access the filesystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    """
    Storage abstraction.

    Responsible for managing uploads, outputs, transcripts,
    subtitles, temporary files, cache, history, logs and
    job-specific files.
    """

    # ==========================================================
    # Uploads
    # ==========================================================

    @abstractmethod
    def save_upload(
        self,
        source_file: Path,
    ) -> Path:
        """
        Save an uploaded file.

        Returns:
            Stored upload path.
        """

    @abstractmethod
    def get_upload(
        self,
        filename: str,
    ) -> Path:
        """
        Retrieve an uploaded file.
        """

    # ==========================================================
    # Output
    # ==========================================================

    @abstractmethod
    def save_output(
        self,
        source_file: Path,
    ) -> Path:
        """
        Save translated output.
        """

    @abstractmethod
    def get_output(
        self,
        filename: str,
    ) -> Path:
        """
        Retrieve translated output.
        """

    # ==========================================================
    # Transcript
    # ==========================================================

    @abstractmethod
    def save_transcript(
        self,
        job_id: str,
        transcript: str,
    ) -> Path:
        """
        Save transcript for a job.
        """

    @abstractmethod
    def get_transcript(
        self,
        job_id: str,
    ) -> str:
        """
        Retrieve transcript.
        """

    # ==========================================================
    # Subtitle
    # ==========================================================

    @abstractmethod
    def save_subtitle(
        self,
        source_file: Path,
    ) -> Path:
        """
        Save subtitle file.
        """

    @abstractmethod
    def get_subtitle(
        self,
        filename: str,
    ) -> Path:
        """
        Retrieve subtitle file.
        """

    # ==========================================================
    # Temporary Files
    # ==========================================================

    @abstractmethod
    def create_temp_file(
        self,
        suffix: str = "",
    ) -> Path:
        """
        Create a temporary file path.
        """

    @abstractmethod
    def delete_temp_file(
        self,
        file_path: Path,
    ) -> None:
        """
        Delete a temporary file.
        """

    # ==========================================================
    # Cache
    # ==========================================================

    @abstractmethod
    def clear_cache(self) -> None:
        """
        Remove cached files.
        """

    # ==========================================================
    # Jobs
    # ==========================================================

    @abstractmethod
    def delete_job_files(
        self,
        job_id: str,
    ) -> None:
        """
        Delete every file associated with a job.
        """

    # ==========================================================
    # Generic Operations
    # ==========================================================

    @abstractmethod
    def exists(
        self,
        path: Path,
    ) -> bool:
        """
        Check whether a file exists.
        """

    @abstractmethod
    def delete(
        self,
        path: Path,
    ) -> None:
        """
        Delete a file.
        """

    @abstractmethod
    def copy(
        self,
        source: Path,
        destination: Path,
    ) -> Path:
        """
        Copy a file.
        """

    @abstractmethod
    def move(
        self,
        source: Path,
        destination: Path,
    ) -> Path:
        """
        Move a file.
        """

    @abstractmethod
    def storage_usage(self) -> dict[str, int]:
        """
        Return storage usage statistics.

        Example
        -------
        {
            "uploads": 12345678,
            "output": 34567890,
            "cache": 987654,
            "total": 46913522
        }
        """