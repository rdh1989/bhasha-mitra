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
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository

from infrastructure.media.video_exporter import VideoExporter
from infrastructure.filesystem.path_manager import PathManager

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue


logger = logging.getLogger(__name__)


class ExportWorker(BaseWorker):
    """
    Processes final video export jobs.
    """

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
                job_id
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
            job_directory
            / "translated_video.mp4"
        )

        logger.info(
            "Starting final video export | "
            "job_id=%s",
            job_id,
        )

        self._video_exporter.export(
            input_video=input_video,
            dubbed_audio=dubbed_audio,
            subtitle_file=subtitle_file,
            output_video=output_video,
        )

        logger.info(
            "Final video export completed | "
            "job_id=%s | output=%s",
            job_id,
            output_video,
        )

    @staticmethod
    def _get_required_artifact(
        job_directory: Path,
        artifact_name: str,
    ) -> Path:
        """
        Resolve a required export artifact.

        The actual artifact filename must be established by the
        preceding workflow stage.
        """

        raise NotImplementedError(
            f"Export artifact resolution for "
            f"'{artifact_name}' has not been defined."
        )