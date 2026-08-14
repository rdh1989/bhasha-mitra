"""
Module:
    path_manager.py

Layer:
    Infrastructure / Filesystem

Description:
    Centralized filesystem path management for Bhasha Mitra.

Responsibilities:
    - Read configured output and database paths
    - Validate configured paths
    - Create application output directories
    - Create per-video directories
    - Create per-translation-job directories
    - Resolve generated file paths
    - Never use a fallback storage path

Output structure:

    <output_path>/
        <video_name>/
            <job_id>/
                final_dubbed.mp4
                <video_name>.srt
                files/
                    audio.wav
                    transcript.json
                    translation.json
                    subtitle.txt
                metadata.txt
"""

from __future__ import annotations

import os
from pathlib import Path

from infrastructure.configuration import configuration


class PathManager:
    """
    Centralized filesystem path manager.
    """

    def __init__(self) -> None:
        """
        Initialize paths from user application configuration.

        No fallback path is used.
        """

        output_path = configuration.get_value(
            "application",
            "output_path",
        )

        database_path = configuration.get_value(
            "application",
            "database_path",
        )

        if not output_path:

            raise RuntimeError(
                "Application output path is not configured."
            )

        if not database_path:

            raise RuntimeError(
                "Application database path is not configured."
            )

        self._output_root = Path(
            output_path
        ).expanduser()

        self._database_path = Path(
            database_path
        ).expanduser()

    # =========================================================================
    # Configured paths
    # =========================================================================

    @property
    def output_root(self) -> Path:
        """
        Configured translated-video output directory.
        """

        return self._output_root

    @property
    def database_path(self) -> Path:
        """
        Configured SQLite database file path.
        """

        return self._database_path

    # =========================================================================
    # Health validation
    # =========================================================================

    def validate(self) -> None:
        """
        Validate configured output and database paths.

        Raises:
            RuntimeError:
                When a configured path is not accessible.
        """

        self._validate_output_path()
        self._validate_database_path()

    def _validate_output_path(self) -> None:
        """
        Validate that the output location is accessible and writable.
        """

        if self._output_root.exists():

            if not self._output_root.is_dir():

                raise RuntimeError(
                    "Configured output path is not a directory: "
                    f"{self._output_root}"
                )

            if not os.access(
                self._output_root,
                os.W_OK,
            ):

                raise RuntimeError(
                    "Configured output path is not writable: "
                    f"{self._output_root}"
                )

            return

        parent = self._output_root.parent

        if not parent.exists():

            raise RuntimeError(
                "Configured output path is not accessible: "
                f"{self._output_root}"
            )

        if not parent.is_dir():

            raise RuntimeError(
                "Parent of configured output path is not a directory: "
                f"{parent}"
            )

        if not os.access(
            parent,
            os.W_OK,
        ):

            raise RuntimeError(
                "Configured output location is not writable: "
                f"{parent}"
            )

    def _validate_database_path(self) -> None:
        """
        Validate the configured database location.

        The database file itself does not need to exist yet.
        """

        parent = self._database_path.parent

        if not parent.exists():

            raise RuntimeError(
                "Configured database path is not accessible: "
                f"{parent}"
            )

        if not parent.is_dir():

            raise RuntimeError(
                "Database path parent is not a directory: "
                f"{parent}"
            )

        if not os.access(
            parent,
            os.W_OK,
        ):

            raise RuntimeError(
                "Configured database location is not writable: "
                f"{parent}"
            )

    # =========================================================================
    # Directory creation
    # =========================================================================

    def ensure_output_root(self) -> Path:
        """
        Create the configured output directory.
        """

        self._output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self._output_root.is_dir():

            raise RuntimeError(
                "Unable to create output directory: "
                f"{self._output_root}"
            )

        return self._output_root

    def ensure_database_directory(self) -> Path:
        """
        Create the configured database parent directory.
        """

        parent = self._database_path.parent

        parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not parent.is_dir():

            raise RuntimeError(
                "Unable to create database directory: "
                f"{parent}"
            )

        return parent

    # =========================================================================
    # Video directory
    # =========================================================================

    def video_directory(
        self,
        video_name: str,
    ) -> Path:
        """
        Return and create the directory belonging to a source video.

        Example:

            movie.mp4
                ↓
            <output_path>/movie/
        """

        name = Path(
            video_name
        ).stem.strip()

        if not name:

            raise ValueError(
                "Video filename cannot be empty."
            )

        path = (
            self._output_root
            / name
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # =========================================================================
    # Translation job directory
    # =========================================================================

    def job_directory(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Return and create the directory belonging to one translation job.

        Example:

            <output_path>/
                movie/
                    8f3c.../
        """

        if not job_id.strip():

            raise ValueError(
                "Job ID cannot be empty."
            )

        path = (
            self.video_directory(video_name)
            / job_id
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # =========================================================================
    # Intermediate files
    # =========================================================================

    def files_directory(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Return and create the intermediate files directory.
        """

        path = (
            self.job_directory(
                video_name,
                job_id,
            )
            / "files"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    def audio_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for extracted audio.
        """

        return (
            self.files_directory(
                video_name,
                job_id,
            )
            / "audio.wav"
        )

    def transcript_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for generated transcript.
        """

        return (
            self.files_directory(
                video_name,
                job_id,
            )
            / "transcript.json"
        )

    def translation_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for generated translation.
        """

        return (
            self.files_directory(
                video_name,
                job_id,
            )
            / "translation.json"
        )

    def subtitle_text_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for generated subtitle text.
        """

        return (
            self.files_directory(
                video_name,
                job_id,
            )
            / "subtitle.txt"
        )

    # =========================================================================
    # Final output files
    # =========================================================================

    def translated_video_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for final translated video.

        Always:

            final_dubbed.mp4
        """

        return (
            self.job_directory(
                video_name,
                job_id,
            )
            / "final_dubbed.mp4"
        )

    def subtitle_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for final SRT subtitle file.

        Example:

            movie.srt
        """

        video_stem = Path(
            video_name
        ).stem

        return (
            self.job_directory(
                video_name,
                job_id,
            )
            / f"{video_stem}.srt"
        )

    def metadata_path(
        self,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Path for final metadata file.
        """

        return (
            self.job_directory(
                video_name,
                job_id,
            )
            / "metadata.txt"
        )