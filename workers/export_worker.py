"""
===============================================================================
BHASHA MITRA
Export Worker
===============================================================================

Module:
    export_worker.py

Layer:
    Workers

Description:
    Background worker responsible for final video export.

Responsibilities:
    - Retrieve export jobs from the export queue
    - Validate required export artifacts
    - Invoke VideoExporter
    - Persist the final translated video path

Important:
    This worker does not perform:
    - Translation
    - Subtitle generation
    - Dubbing / TTS

    Those stages must complete before export starts.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository

from infrastructure.configuration.configuration_manager import (
    ConfigurationManager,
)
from infrastructure.media.video_exporter import VideoExporter
from infrastructure.filesystem.path_manager import PathManager

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue


logger = logging.getLogger(__name__)


class ExportWorker(BaseWorker):
    """
    Processes final video export jobs.
    """

    # =========================================================================
    # Windows file-lock protection
    # =========================================================================

    ARTIFACT_READY_RETRIES = 30
    ARTIFACT_READY_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        job_queue: JobQueue[str],
        job_repository: JobRepository,
        video_exporter: VideoExporter,
        path_manager: PathManager,
    ) -> None:

        super().__init__("export")

        self._job_queue = job_queue
        self._job_repository = job_repository
        self._video_exporter = video_exporter
        self._path_manager = path_manager

    def run(self) -> None:
        """
        Main export worker loop.
        """

        logger.info(
            "Export worker started."
        )

        while self.is_running:

            job_id = self._job_queue.get(
                timeout=1
            )

            if job_id is None:
                continue

            try:

                self.process_job(
                    job_id
                )

            except Exception:

                logger.exception(
                    "Export failed | job_id=%s",
                    job_id,
                )

            finally:

                self._job_queue.task_done()

        logger.info(
            "Export worker stopped."
        )

    def process_job(
        self,
        job_id: str,
    ) -> None:
        """
        Export the final translated video.

        Required subtitle and dubbed-audio artifact paths must be
        provided by the completed translation workflow.
        """

        job = self._job_repository.get(
            job_id
        )

        if job is None:

            logger.warning(
                "Export job not found | job_id=%s",
                job_id,
            )

            return

        job_directory = (
            self._path_manager.job_directory(
                job.input_file.name,
                job.id,
            )
        )

        # ---------------------------------------------------------------------
        # Required export artifacts
        #
        # These paths are intentionally not guessed here.
        # The translation workflow must establish the actual artifact paths
        # before queuing the export job.
        # ---------------------------------------------------------------------

        subtitle_file = self._get_required_artifact(
            job_directory,
            "subtitle_file",
        )

        dubbed_audio = self._get_required_artifact(
            job_directory,
            "dubbed_audio",
        )

        input_video = Path(
            job.input_file
        )

        if not input_video.is_file():

            raise FileNotFoundError(
                f"Input video not found: {input_video}"
            )

        # ---------------------------------------------------------------------
        # Output
        # ---------------------------------------------------------------------

        output_video = (
            self._path_manager.translated_video_path(
                job.input_file.name,
                job.id,
            )
        )

        # ---------------------------------------------------------------------
        # Wait out any transient Windows file lock (WinError 32) left behind
        # by the AI Framework/upstream workers before FFmpeg opens the files.
        # ---------------------------------------------------------------------

        for artifact_path in (input_video, dubbed_audio, subtitle_file):

            self._wait_until_readable(
                artifact_path,
                job_id=job_id,
            )

        logger.info(
            "Starting final video export | "
            "job_id=%s",
            job_id,
        )

        subtitle_language, subtitle_title = (
            self._resolve_subtitle_language(
                job.target_language
            )
        )

        self._video_exporter.export(
            input_video=input_video,
            dubbed_audio=dubbed_audio,
            subtitle_file=subtitle_file,
            output_video=output_video,
            subtitle_language=subtitle_language,
            subtitle_title=subtitle_title,
        )

        logger.info(
            "Final video export completed | "
            "job_id=%s | output=%s",
            job_id,
            output_video,
        )

        job.complete(
            output_video
        )

        self._job_repository.save(
            job
        )

    @staticmethod
    def _resolve_subtitle_language(
        target_language: str,
    ) -> tuple[str | None, str | None]:
        """
        Derive the muxed subtitle stream's language code/title.

        Reuses config/languages.yaml (same source as the NLLB code map)
        instead of introducing a second language registry. The FLORES-200
        `nllb_code` (e.g. "mar_Deva") already carries the ISO 639-2 code as
        its prefix, which MP4 subtitle metadata expects (e.g. "mar").
        """

        languages = (
            ConfigurationManager().languages.get("languages")
            or {}
        )

        entry = languages.get(target_language) or {}

        nllb_code = entry.get("nllb_code")

        language_code = (
            nllb_code.split("_")[0]
            if nllb_code
            else target_language
        )

        return language_code, entry.get("name")

    @staticmethod
    def _get_required_artifact(
        job_directory: Path,
        artifact_name: str,
    ) -> Path:
        """
        Resolve a required export artifact.

        The actual artifact filename must be established by the
        preceding workflow stage, inside the job's `files` directory.
        """

        files_directory = job_directory / "files"

        if artifact_name == "dubbed_audio":

            artifact_path = files_directory / "dubbed_audio.wav"

            if not artifact_path.is_file():

                raise FileNotFoundError(
                    f"Dubbed audio artifact not found: {artifact_path}"
                )

            return artifact_path

        if artifact_name == "subtitle_file":

            matches = sorted(
                files_directory.glob("subtitle.*")
            )

            if not matches:

                raise FileNotFoundError(
                    "Subtitle artifact not found in: "
                    f"{files_directory}"
                )

            return matches[0]

        raise ValueError(
            f"Unknown export artifact: {artifact_name}"
        )

    def _wait_until_readable(
        self,
        file_path: Path,
        job_id: str,
    ) -> None:
        """
        Block until an artifact is free of a Windows sharing violation.

        FFmpeg opens every input file itself; if an upstream writer (AI
        Framework or a prior worker) briefly retains a handle, FFmpeg would
        otherwise fail with WinError 32. Only ERROR_SHARING_VIOLATION /
        ERROR_LOCK_VIOLATION is retried here.
        """

        for attempt in range(
            1,
            self.ARTIFACT_READY_RETRIES + 1,
        ):

            try:

                with file_path.open("rb"):
                    return

            except PermissionError as exc:

                if getattr(exc, "winerror", None) != 32:
                    raise

                if attempt == self.ARTIFACT_READY_RETRIES:

                    logger.error(
                        "EXPORT ARTIFACT REMAINS LOCKED | "
                        "job_id=%s | attempts=%d | file=%s",
                        job_id,
                        self.ARTIFACT_READY_RETRIES,
                        file_path,
                    )

                    raise

                logger.warning(
                    "EXPORT ARTIFACT LOCKED | "
                    "job_id=%s | attempt=%d/%d | file=%s | retry_in=%.1fs",
                    job_id,
                    attempt,
                    self.ARTIFACT_READY_RETRIES,
                    file_path,
                    self.ARTIFACT_READY_RETRY_DELAY_SECONDS,
                )

                time.sleep(
                    self.ARTIFACT_READY_RETRY_DELAY_SECONDS
                )