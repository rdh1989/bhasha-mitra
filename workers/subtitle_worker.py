"""
===============================================================================
BHASHA MITRA

Module:
    subtitle_worker.py

Layer:
    Workers

Description:
    Executes subtitle generation after translation.

Workflow:

    translation.json
          |
          v
    SubtitleClient
          |
          v
    AI Framework /subtitle
          |
          v
    subtitle artifact
          |
          v
    job/files/subtitle.*

Backend owns:
    - Queue processing
    - Workflow invocation
    - Artifact persistence
    - Error logging

AI Framework owns:
    - Subtitle generation
    - Subtitle file creation

Important:
    This worker does NOT own the overall TranslationJob state.
    Subtitle and Dubbing are parallel downstream stages.
    Overall workflow state should be coordinated by the orchestrator.
===============================================================================
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from app.application.interfaces.job_repository import (
    JobRepository,
)

from domain.entities import TranslationJob

from infrastructure.ai.subtitle_client import (
    SubtitleClient,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue


logger = logging.getLogger(__name__)


class SubtitleWorker(BaseWorker):
    """
    Executes subtitle generation jobs.
    """

    # =========================================================================
    # Windows file-lock protection
    # =========================================================================

    SUBTITLE_COPY_RETRIES = 30
    SUBTITLE_COPY_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        job_queue: JobQueue[str],
        dubbing_queue: JobQueue[str],
        job_repository: JobRepository,
        subtitle_client: SubtitleClient,
        path_manager: PathManager,
    ) -> None:

        super().__init__("subtitle")

        self._job_queue = job_queue
        self._dubbing_queue = dubbing_queue
        self._job_repository = job_repository
        self._subtitle_client = subtitle_client
        self._path_manager = path_manager

    # =========================================================================
    # Subtitle artifact copy
    # =========================================================================

    def _copy_subtitle_artifact(
        self,
        source: Path,
        destination: Path,
        job_id: str,
    ) -> None:
        """
        Persist the AI-generated subtitle artifact safely on Windows.

        The AI Framework must close the subtitle file before returning the
        API response. This retry protects against a short-lived Windows
        file lock that can remain immediately after generation.
        """

        for attempt in range(
            1,
            self.SUBTITLE_COPY_RETRIES + 1,
        ):

            try:

                logger.info(
                    "SUBTITLE ARTIFACT COPY ATTEMPT | "
                    "job_id=%s | attempt=%d/%d | "
                    "source=%s | destination=%s",
                    job_id,
                    attempt,
                    self.SUBTITLE_COPY_RETRIES,
                    source,
                    destination,
                )

                shutil.copy2(
                    source,
                    destination,
                )

                logger.info(
                    "SUBTITLE ARTIFACT COPY SUCCEEDED | "
                    "job_id=%s | attempt=%d",
                    job_id,
                    attempt,
                )

                return

            except PermissionError as exc:

                # Only retry Windows ERROR_SHARING_VIOLATION /
                # ERROR_LOCK_VIOLATION. Do not hide unrelated permission
                # problems.
                if getattr(exc, "winerror", None) != 32:
                    raise

                if attempt == self.SUBTITLE_COPY_RETRIES:
                    logger.error(
                        "SUBTITLE ARTIFACT COPY FAILED - "
                        "SOURCE REMAINS LOCKED | "
                        "job_id=%s | attempts=%d | source=%s",
                        job_id,
                        self.SUBTITLE_COPY_RETRIES,
                        source,
                    )
                    raise

                logger.warning(
                    "SUBTITLE ARTIFACT SOURCE LOCKED | "
                    "job_id=%s | attempt=%d/%d | retry_in=%.1fs",
                    job_id,
                    attempt,
                    self.SUBTITLE_COPY_RETRIES,
                    self.SUBTITLE_COPY_RETRY_DELAY_SECONDS,
                )

                time.sleep(
                    self.SUBTITLE_COPY_RETRY_DELAY_SECONDS
                )

    # =========================================================================
    # Background worker
    # =========================================================================

    def run(self) -> None:
        """
        Process queued subtitle jobs.
        """

        logger.info(
            "SUBTITLE WORKER STARTED"
        )

        while self.is_running:

            job_id = self._job_queue.get(
                timeout=1
            )

            if job_id is None:
                continue

            logger.info(
                "SUBTITLE JOB PICKED FROM QUEUE | "
                "job_id=%s",
                job_id,
            )

            try:

                job = self._job_repository.get(
                    job_id
                )

                if job is None:

                    logger.warning(
                        "SUBTITLE JOB NOT FOUND | "
                        "job_id=%s",
                        job_id,
                    )

                    continue

                logger.info(
                    "SUBTITLE JOB LOADED | "
                    "job_id=%s | "
                    "source=%s | "
                    "target=%s",
                    job.id,
                    job.source_language,
                    job.target_language,
                )

                self.execute(
                    job
                )

            except Exception as exc:

                logger.exception(
                    "SUBTITLE GENERATION FAILED | "
                    "job_id=%s | "
                    "error_type=%s | "
                    "error=%s",
                    job_id,
                    type(exc).__name__,
                    exc,
                )

            finally:

                self._job_queue.task_done()

                logger.info(
                    "SUBTITLE QUEUE TASK COMPLETED | "
                    "job_id=%s",
                    job_id,
                )

        logger.info(
            "SUBTITLE WORKER STOPPED"
        )

    # =========================================================================
    # Subtitle stage
    # =========================================================================

    def execute(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute subtitle generation for one job.
        """

        start_time = time.monotonic()

        logger.info(
            "SUBTITLE STAGE STARTED | "
            "job_id=%s | "
            "target_language=%s",
            job.id,
            job.target_language,
        )

        # =====================================================================
        # Locate translation artifact
        # =====================================================================

        translation_file = (
            self._path_manager.job_directory(
                job.input_file.name,
                job.id,
            )
            / "files"
            / "translation.json"
        )

        logger.info(
            "SUBTITLE TRANSLATION FILE CHECK | "
            "job_id=%s | "
            "translation=%s",
            job.id,
            translation_file,
        )

        if not translation_file.is_file():

            raise FileNotFoundError(
                "Translation file does not exist: "
                f"{translation_file}"
            )

        logger.info(
            "SUBTITLE TRANSLATION FILE VALIDATED | "
            "job_id=%s | "
            "size=%d bytes",
            job.id,
            translation_file.stat().st_size,
        )

        # =====================================================================
        # Subtitle format
        # =====================================================================

        subtitle_format = "srt"

        logger.info(
            "SUBTITLE FORMAT SELECTED | "
            "job_id=%s | "
            "format=%s | "
            "language=%s",
            job.id,
            subtitle_format,
            job.target_language,
        )

        # =====================================================================
        # Call AI Framework
        # =====================================================================

        logger.warning(
            "SUBTITLE API REQUEST STARTED | "
            "job_id=%s | "
            "translation=%s | "
            "format=%s | "
            "language=%s",
            job.id,
            translation_file,
            subtitle_format,
            job.target_language,
        )

        api_start = time.monotonic()

        try:

            result = (
                self._subtitle_client.generate(
                    translation_path=str(
                        translation_file
                    ),
                    subtitle_format=subtitle_format,
                    language=job.target_language,
                )
            )

        except Exception:

            api_elapsed = (
                time.monotonic() - api_start
            )

            logger.exception(
                "SUBTITLE API REQUEST FAILED | "
                "job_id=%s | "
                "elapsed=%.2fs",
                job.id,
                api_elapsed,
            )

            raise

        api_elapsed = (
            time.monotonic() - api_start
        )

        logger.warning(
            "SUBTITLE API RESPONSE RECEIVED | "
            "job_id=%s | "
            "elapsed=%.2fs | "
            "result_type=%s",
            job.id,
            api_elapsed,
            type(result).__name__,
        )

        # =====================================================================
        # Validate response
        # =====================================================================

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Subtitle API returned an invalid response."
            )

        api_status = result.get(
            "status"
        )

        logger.info(
            "SUBTITLE API RESPONSE VALIDATING | "
            "job_id=%s | "
            "status=%s",
            job.id,
            api_status,
        )

        if api_status != "PASS":

            raise RuntimeError(
                "Subtitle API did not return PASS."
            )

        source_subtitle_path = result.get(
            "subtitle_path"
        )

        if not source_subtitle_path:

            raise RuntimeError(
                "Subtitle API did not return "
                "subtitle_path."
            )

        source_subtitle = (
            Path(
                source_subtitle_path
            )
            .expanduser()
            .resolve()
        )

        logger.info(
            "SUBTITLE API ARTIFACT RECEIVED | "
            "job_id=%s | "
            "source=%s",
            job.id,
            source_subtitle,
        )

        if not source_subtitle.is_file():

            raise FileNotFoundError(
                "Subtitle API returned a subtitle "
                "path that does not exist: "
                f"{source_subtitle}"
            )

        # =====================================================================
        # Determine output extension
        # =====================================================================

        extension = (
            source_subtitle.suffix
            or ".srt"
        )

        subtitle_file = (
            self._path_manager.job_directory(
                job.input_file.name,
                job.id,
            )
            / "files"
            / f"subtitle{extension}"
        )

        subtitle_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "SUBTITLE ARTIFACT DESTINATION PREPARED | "
            "job_id=%s | "
            "destination=%s",
            job.id,
            subtitle_file,
        )

        # =====================================================================
        # Persist artifact
        # =====================================================================
        #
        # The AI Framework may write subtitle.<ext> directly into the
        # Backend's final job/files directory. If that happens, source and
        # destination are the SAME file.
        #
        # Never call shutil.copy2(source, source). On Windows this can
        # produce WinError 32 even though the AI Framework already closed
        # the file, because the destination is opened for writing while it
        # is still being read as the source.
        # =====================================================================

        source_subtitle = source_subtitle.resolve()
        subtitle_file = subtitle_file.resolve()

        if source_subtitle == subtitle_file:

            logger.info(
                "SUBTITLE ARTIFACT ALREADY IN FINAL LOCATION | "
                "job_id=%s | "
                "path=%s | "
                "copy_skipped=True",
                job.id,
                subtitle_file,
            )

        else:

            logger.info(
                "SUBTITLE ARTIFACT COPY STARTED | "
                "job_id=%s | "
                "source=%s | "
                "destination=%s",
                job.id,
                source_subtitle,
                subtitle_file,
            )

            self._copy_subtitle_artifact(
                source=source_subtitle,
                destination=subtitle_file,
                job_id=job.id,
            )

        if not subtitle_file.is_file():

            raise RuntimeError(
                "Subtitle artifact was not created."
            )

        elapsed = (
            time.monotonic() - start_time
        )

        logger.info(
            "SUBTITLE ARTIFACT CREATED | "
            "job_id=%s | "
            "subtitle=%s | "
            "size=%d bytes",
            job.id,
            subtitle_file,
            subtitle_file.stat().st_size,
        )

        logger.warning(
            "SUBTITLE STAGE COMPLETED | "
            "job_id=%s | "
            "subtitle=%s | "
            "elapsed=%.2fs",
            job.id,
            subtitle_file,
            elapsed,
        )

        # =====================================================================
        # Queue Dubbing
        # =====================================================================

        logger.warning(
            "DUBBING QUEUE REQUESTED | "
            "job_id=%s | "
            "target_language=%s",
            job.id,
            job.target_language,
        )

        self._dubbing_queue.put(
            job.id
        )

        logger.warning(
            "JOB QUEUED FOR DUBBING | "
            "job_id=%s | "
            "target_language=%s",
            job.id,
            job.target_language,
        )

        logger.info(
            "SUBTITLE WORKER HANDOFF READY | "
            "job_id=%s | "
            "next_stage=VIDEO_ASSEMBLY",
            job.id,
        )