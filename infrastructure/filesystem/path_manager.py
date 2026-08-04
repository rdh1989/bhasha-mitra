"""
Centralized Storage Path Manager.

Responsible for resolving every storage location used
throughout Bhasha Mitra.

No other component should hardcode storage paths.
"""

from __future__ import annotations

from pathlib import Path


class PathManager:
    """
    Provides strongly typed access to application storage paths.
    """

    def __init__(
        self,
        storage_root: Path,
    ) -> None:

        self._root = storage_root

        self._uploads = self._root / "uploads"
        self._output = self._root / "output"
        self._transcripts = self._root / "transcripts"
        self._subtitles = self._root / "subtitles"
        self._temp = self._root / "temp"
        self._cache = self._root / "cache"
        self._history = self._root / "history"
        self._logs = self._root / "logs"
        self._jobs = self._root / "jobs"

        self._create_directories()

    # ==========================================================
    # Public Properties
    # ==========================================================

    @property
    def uploads(self) -> Path:
        return self._uploads

    @property
    def output(self) -> Path:
        return self._output

    @property
    def transcripts(self) -> Path:
        return self._transcripts

    @property
    def subtitles(self) -> Path:
        return self._subtitles

    @property
    def temp(self) -> Path:
        return self._temp

    @property
    def cache(self) -> Path:
        return self._cache

    @property
    def history(self) -> Path:
        return self._history

    @property
    def logs(self) -> Path:
        return self._logs

    @property
    def jobs(self) -> Path:
        return self._jobs

    # ==========================================================
    # Job Specific Paths
    # ==========================================================

    def job_directory(
        self,
        job_id: str,
    ) -> Path:
        """
        Return the directory dedicated to one job.
        """

        path = self.jobs / job_id
        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    def transcript_file(
        self,
        job_id: str,
    ) -> Path:
        return self.transcripts / f"{job_id}.txt"

    def subtitle_file(
        self,
        job_id: str,
    ) -> Path:
        return self.subtitles / f"{job_id}.srt"

    def output_file(
        self,
        filename: str,
    ) -> Path:
        return self.output / filename

    def upload_file(
        self,
        filename: str,
    ) -> Path:
        return self.uploads / filename

    # ==========================================================
    # Internal
    # ==========================================================

    def _create_directories(
        self,
    ) -> None:

        directories = (
            self.uploads,
            self.output,
            self.transcripts,
            self.subtitles,
            self.temp,
            self.cache,
            self.history,
            self.logs,
            self.jobs,
        )

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )