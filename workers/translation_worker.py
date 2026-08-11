"""
===============================================================================
BHASHA MITRA

Module:
    translation_worker.py

Layer:
    Workers

Description:
    Executes the translation stage after transcript generation.

Workflow:

    Translation Queue
            ↓
       QUEUED → RUNNING
            ↓
       AI Translation
            ↓
      translation.json
            ↓
       RUNNING → COMPLETED
            ↓
       Dubbing Queue

AI Contract:
    POST /translate

The AI Framework handles:
    - Long-text/context grouping
    - Translation
    - Translation artifact generation

Backend owns:
    - Workflow invocation
    - Translation artifact persistence
    - Job state
    - Translation-stage logging
    - Dubbing queue handoff
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

from infrastructure.ai.translation_client import (
    TranslationClient,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue


logger = logging.getLogger(__name__)


class TranslationWorker(BaseWorker):
    """
    Executes the translation stage.
    """

    # =========================================================================
    # Windows file-lock protection
    # =========================================================================

    TRANSLATION_COPY_RETRIES = 30
    TRANSLATION_COPY_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        job_queue: JobQueue[str],
        dubbing_queue: JobQueue[str],
        job_repository: JobRepository,
        translation_client: TranslationClient,
        path_manager: PathManager,
    ) -> None:

        super().__init__("translation")

        self._job_queue = job_queue
        self._dubbing_queue = dubbing_queue
        self._job_repository = job_repository
        self._translation_client = translation_client
        self._path_manager = path_manager

    # =========================================================================
    # Background worker
    # =========================================================================

    def run(self) -> None:
        """
        Process queued translation jobs.
        """

        logger.info(
            "TRANSLATION WORKER STARTED"
        )

        while self.is_running:

            job_id = self._job_queue.get(
                timeout=1
            )

            if job_id is None:
                continue

            logger.info(
                "TRANSLATION JOB PICKED FROM QUEUE | "
                "job_id=%s",
                job_id,
            )

            try:

                job = self._job_repository.get(
                    job_id
                )

                if job is None:

                    logger.warning(
                        "TRANSLATION JOB NOT FOUND | "
                        "job_id=%s",
                        job_id,
                    )

                    continue

                logger.info(
                    "TRANSLATION JOB LOADED | "
                    "job_id=%s | "
                    "status=%s | "
                    "source=%s | "
                    "target=%s",
                    job.id,
                    job.status.value,
                    job.source_language,
                    job.target_language,
                )

                self.execute(
                    job
                )

            except Exception as exc:

                logger.exception(
                    "TRANSLATION FAILED | "
                    "job_id=%s | "
                    "error_type=%s | "
                    "error=%s",
                    job_id,
                    type(exc).__name__,
                    exc,
                )

                self._mark_failed(
                    job_id,
                    str(exc),
                )

            finally:

                self._job_queue.task_done()

                logger.info(
                    "TRANSLATION QUEUE TASK COMPLETED | "
                    "job_id=%s",
                    job_id,
                )

        logger.info(
            "TRANSLATION WORKER STOPPED"
        )

    # =========================================================================
    # Translation stage
    # =========================================================================

    def execute(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute one translation stage.
        """

        start_time = time.monotonic()

        logger.info(
            "TRANSLATION STAGE STARTED | "
            "job_id=%s | "
            "source=%s | "
            "target=%s",
            job.id,
            job.source_language,
            job.target_language,
        )

        # =====================================================================
        # Job state
        # =====================================================================
        #
        # IMPORTANT:
        #
        # Preprocessing queues the job before placing it into the
        # translation queue.
        #
        # Therefore the expected state is:
        #
        #     PENDING → QUEUED → RUNNING
        #
        # NOT:
        #
        #     PENDING → RUNNING
        #
        # =====================================================================

        logger.info(
            "TRANSLATION JOB STATE CHECK | "
            "job_id=%s | "
            "current_status=%s",
            job.id,
            job.status.value,
        )

        if job.status.value == "QUEUED":

            logger.info(
                "TRANSLATION JOB STARTING | "
                "job_id=%s | "
                "transition=QUEUED_TO_RUNNING",
                job.id,
            )

            job.start()

            self._job_repository.save(
                job
            )

            logger.info(
                "TRANSLATION JOB RUNNING | "
                "job_id=%s | "
                "status=%s",
                job.id,
                job.status.value,
            )

        elif job.status.value == "RUNNING":

            logger.info(
                "TRANSLATION JOB ALREADY RUNNING | "
                "job_id=%s",
                job.id,
            )

        else:

            raise RuntimeError(
                "Translation job is not in a valid "
                f"translation state: {job.status.value}"
            )

        # =====================================================================
        # Preconditions
        # =====================================================================

        transcript_file = (
            job.preprocessing.transcript_file
        )

        logger.info(
            "TRANSLATION PRECONDITION CHECK | "
            "job_id=%s | "
            "transcript=%s",
            job.id,
            transcript_file,
        )

        if transcript_file is None:

            raise RuntimeError(
                "Transcript file is not available."
            )

        transcript_file = (
            Path(
                transcript_file
            )
            .expanduser()
            .resolve()
        )

        if not transcript_file.is_file():

            raise FileNotFoundError(
                "Transcript file does not exist: "
                f"{transcript_file}"
            )

        logger.info(
            "TRANSLATION TRANSCRIPT VALIDATED | "
            "job_id=%s | "
            "transcript=%s | "
            "size=%d bytes",
            job.id,
            transcript_file,
            transcript_file.stat().st_size,
        )

        # =====================================================================
        # Final translation artifact
        # =====================================================================

        translation_file = (
            self._path_manager.job_directory(
                job.input_file.name,
                job.id,
            )
            / "files"
            / "translation.json"
        )

        translation_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "TRANSLATION ARTIFACT PATH PREPARED | "
            "job_id=%s | "
            "translation=%s",
            job.id,
            translation_file,
        )

        # =====================================================================
        # Validate language information
        # =====================================================================

        if not job.source_language:

            raise RuntimeError(
                "Source language is not available."
            )

        if not job.target_language:

            raise RuntimeError(
                "Target language is not available."
            )

        logger.info(
            "TRANSLATION LANGUAGES VALIDATED | "
            "job_id=%s | "
            "source=%s | "
            "target=%s",
            job.id,
            job.source_language,
            job.target_language,
        )

        # =====================================================================
        # Call AI Framework
        # =====================================================================

        logger.warning(
            "TRANSLATION API REQUEST STARTED | "
            "job_id=%s | "
            "transcript=%s | "
            "source=%s | "
            "target=%s",
            job.id,
            transcript_file,
            job.source_language,
            job.target_language,
        )

        api_start = time.monotonic()

        try:

            result = (
                self._translation_client.translate(
                    transcript_path=str(
                        transcript_file
                    ),
                    source_language=(
                        job.source_language
                    ),
                    target_language=(
                        job.target_language
                    ),
                )
            )

        except Exception:

            api_elapsed = (
                time.monotonic()
                - api_start
            )

            logger.exception(
                "TRANSLATION API REQUEST FAILED | "
                "job_id=%s | "
                "elapsed=%.2fs",
                job.id,
                api_elapsed,
            )

            raise

        api_elapsed = (
            time.monotonic()
            - api_start
        )

        logger.warning(
            "TRANSLATION API RESPONSE RECEIVED | "
            "job_id=%s | "
            "elapsed=%.2fs | "
            "result_type=%s",
            job.id,
            api_elapsed,
            type(result).__name__,
        )

        # =====================================================================
        # Validate AI response
        # =====================================================================

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Translation API returned "
                "an invalid response."
            )

        logger.info(
            "TRANSLATION API RESPONSE VALIDATING | "
            "job_id=%s | "
            "status=%s",
            job.id,
            result.get("status"),
        )

        if result.get("status") != "PASS":

            error_message = (
                str(
                    result.get("error_message")
                    or result.get("detail")
                    or "Translation API did not return PASS."
                )
            )

            raise RuntimeError(
                error_message
            )

        source_translation_path = (
            result.get(
                "translation_path"
            )
        )

        if not source_translation_path:

            raise RuntimeError(
                "Translation API did not return "
                "translation_path."
            )

        source_translation = (
            Path(
                source_translation_path
            )
            .expanduser()
            .resolve()
        )

        logger.info(
            "TRANSLATION API ARTIFACT RECEIVED | "
            "job_id=%s | "
            "source_translation=%s",
            job.id,
            source_translation,
        )

        if not source_translation.is_file():

            raise FileNotFoundError(
                "Translation API returned a "
                "translation path that does not exist: "
                f"{source_translation}"
            )

        logger.info(
            "TRANSLATION SOURCE ARTIFACT VALIDATED | "
            "job_id=%s | "
            "size=%d bytes",
            job.id,
            source_translation.stat().st_size,
        )

        # =====================================================================
        # Persist artifact
        # =====================================================================

        # =====================================================================
        # Persist artifact
        # =====================================================================
        #
        # The AI Framework may create translation.json directly in the
        # Backend's final job directory. If that happens, source and
        # destination are the SAME file.
        #
        # Never call shutil.copy2(source, source). On Windows this can
        # produce WinError 32 and incorrectly fail an otherwise successful
        # translation.
        # =====================================================================

        source_translation = source_translation.resolve()
        translation_file = translation_file.resolve()

        if source_translation == translation_file:

            logger.info(
                "TRANSLATION ARTIFACT ALREADY IN FINAL LOCATION | "
                "job_id=%s | "
                "path=%s | "
                "copy_skipped=True",
                job.id,
                translation_file,
            )

        else:

            logger.info(
                "TRANSLATION ARTIFACT COPY STARTED | "
                "job_id=%s | "
                "source=%s | "
                "destination=%s",
                job.id,
                source_translation,
                translation_file,
            )

            self._copy_translation_artifact(
                source=source_translation,
                destination=translation_file,
                job_id=job.id,
            )

        if not translation_file.is_file():

            raise RuntimeError(
                "Translation artifact was not created."
            )

        # Verify that the final artifact can be opened before completing
        # the translation job and handing it to downstream workers.
        try:

            with translation_file.open(
                "rb"
            ) as artifact:

                artifact.read(1)

        except PermissionError as exc:

            if getattr(exc, "winerror", None) == 32:

                raise RuntimeError(
                    "Translation artifact is still locked. "
                    "The AI Framework must close translation.json "
                    "before returning the /translate response."
                ) from exc

            raise

        # Verify the final artifact is readable before handing the job to
        # downstream Subtitle/Dubbing stages. If the AI Framework still has
        # the file open, fail with a clear integration error rather than
        # allowing a later worker to fail mysteriously.
        try:

            with translation_file.open("rb") as artifact:
                artifact.read(1)

        except PermissionError as exc:

            if getattr(exc, "winerror", None) == 32:

                raise RuntimeError(
                    "Translation artifact is still locked. "
                    "The AI Framework must close translation.json "
                    "before returning the /translate response."
                ) from exc

            raise

        logger.info(
            "TRANSLATION ARTIFACT CREATED | "
            "job_id=%s | "
            "translation=%s | "
            "size=%d bytes",
            job.id,
            translation_file,
            translation_file.stat().st_size,
        )

        # =====================================================================
        # Complete translation job
        # =====================================================================

        logger.info(
            "TRANSLATION JOB COMPLETION STARTED | "
            "job_id=%s | "
            "current_status=%s",
            job.id,
            job.status.value,
        )

        job.complete(
            output_file=translation_file
        )

        self._job_repository.save(
            job
        )

        logger.warning(
            "TRANSLATION JOB COMPLETED | "
            "job_id=%s | "
            "status=%s | "
            "translation=%s",
            job.id,
            job.status.value,
            translation_file,
        )

        # =====================================================================
        # Queue Dubbing
        # =====================================================================

        logger.warning(
            "DUBBING QUEUE REQUESTED | "
            "job_id=%s | "
            "translation=%s | "
            "target_language=%s",
            job.id,
            translation_file,
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

        # =====================================================================
        # Completed
        # =====================================================================

        elapsed = (
            time.monotonic()
            - start_time
        )

        logger.warning(
            "TRANSLATION STAGE COMPLETED | "
            "job_id=%s | "
            "source=%s | "
            "target=%s | "
            "translation=%s | "
            "elapsed=%.2fs",
            job.id,
            job.source_language,
            job.target_language,
            translation_file,
            elapsed,
        )

    # =========================================================================
    # Translation artifact persistence
    # =========================================================================

    def _copy_translation_artifact(
        self,
        source: Path,
        destination: Path,
        job_id: str,
    ) -> None:
        """
        Persist the AI-generated translation artifact safely on Windows.

        Rules:
        1. Never copy a file onto itself.
        2. If source and destination are different, copy using a temporary
           file in the destination directory and atomically replace the
           destination.
        3. Retry only WinError 32 (temporary source lock).
        4. Do not mask other PermissionError causes.
        """

        source = source.expanduser().resolve()
        destination = destination.expanduser().resolve()

        # -----------------------------------------------------------------
        # Most important protection:
        # AI Framework may already have produced translation.json directly
        # at the Backend's final location.
        # -----------------------------------------------------------------

        if source == destination:

            logger.info(
                "TRANSLATION ARTIFACT COPY SKIPPED | "
                "job_id=%s | "
                "reason=SOURCE_EQUALS_DESTINATION | "
                "path=%s",
                job_id,
                source,
            )

            return

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_destination = (
            destination.with_name(
                f".{destination.name}.{job_id}.tmp"
            )
        )

        last_error: PermissionError | None = None

        for attempt in range(
            1,
            self.TRANSLATION_COPY_RETRIES + 1,
        ):

            try:

                # Remove a stale temporary file from a previous attempt.
                if temporary_destination.exists():

                    try:
                        temporary_destination.unlink()

                    except PermissionError as exc:

                        if getattr(exc, "winerror", None) != 32:
                            raise

                        last_error = exc

                        if attempt >= self.TRANSLATION_COPY_RETRIES:
                            raise

                        logger.warning(
                            "TRANSLATION TEMP FILE LOCKED | "
                            "job_id=%s | "
                            "attempt=%d/%d | "
                            "retry_in=%.1fs",
                            job_id,
                            attempt,
                            self.TRANSLATION_COPY_RETRIES,
                            self.TRANSLATION_COPY_RETRY_DELAY_SECONDS,
                        )

                        time.sleep(
                            self.TRANSLATION_COPY_RETRY_DELAY_SECONDS
                        )

                        continue

                logger.info(
                    "TRANSLATION ARTIFACT COPY ATTEMPT | "
                    "job_id=%s | "
                    "attempt=%d/%d | "
                    "source=%s | "
                    "temporary=%s",
                    job_id,
                    attempt,
                    self.TRANSLATION_COPY_RETRIES,
                    source,
                    temporary_destination,
                )

                # Copy to a separate temporary file first. This prevents
                # partial destination artifacts if the copy is interrupted.
                shutil.copy2(
                    source,
                    temporary_destination,
                )

                # os.replace is atomic on the same Windows filesystem.
                # Import locally to keep this helper self-contained.
                import os

                os.replace(
                    temporary_destination,
                    destination,
                )

                logger.info(
                    "TRANSLATION ARTIFACT COPY SUCCEEDED | "
                    "job_id=%s | "
                    "attempt=%d | "
                    "destination=%s",
                    job_id,
                    attempt,
                    destination,
                )

                return

            except PermissionError as exc:

                last_error = exc

                # Only retry the specific Windows sharing violation.
                if getattr(exc, "winerror", None) != 32:
                    raise

                if attempt >= self.TRANSLATION_COPY_RETRIES:

                    logger.error(
                        "TRANSLATION ARTIFACT COPY FAILED - "
                        "WINDOWS FILE LOCK PERSISTED | "
                        "job_id=%s | "
                        "attempts=%d | "
                        "source=%s | "
                        "destination=%s",
                        job_id,
                        self.TRANSLATION_COPY_RETRIES,
                        source,
                        destination,
                    )

                    raise RuntimeError(
                        "Translation artifact remained locked by "
                        "another process after all retry attempts. "
                        "The AI Framework must close the artifact "
                        "before returning the /translate response."
                    ) from exc

                logger.warning(
                    "TRANSLATION ARTIFACT SOURCE LOCKED | "
                    "job_id=%s | "
                    "attempt=%d/%d | "
                    "retry_in=%.1fs | "
                    "source=%s",
                    job_id,
                    attempt,
                    self.TRANSLATION_COPY_RETRIES,
                    self.TRANSLATION_COPY_RETRY_DELAY_SECONDS,
                    source,
                )

                time.sleep(
                    self.TRANSLATION_COPY_RETRY_DELAY_SECONDS
                )

        if last_error is not None:
            raise RuntimeError(
                "Translation artifact copy failed because "
                "the file remained locked."
            ) from last_error

        raise RuntimeError(
            "Translation artifact copy failed unexpectedly."
        )

    # =========================================================================
    # Failure
    # =========================================================================

    def _mark_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> None:
        """
        Mark translation failure in the job repository.

        Expected state at failure:

            RUNNING → FAILED
        """

        job = self._job_repository.get(
            job_id
        )

        if job is None:

            logger.warning(
                "CANNOT MARK TRANSLATION FAILED | "
                "JOB NOT FOUND | "
                "job_id=%s",
                job_id,
            )

            return

        logger.error(
            "MARKING TRANSLATION JOB FAILED | "
            "job_id=%s | "
            "current_status=%s | "
            "error=%s",
            job_id,
            job.status.value,
            error_message,
        )

        try:

            # -------------------------------------------------------------
            # Defensive recovery.
            #
            # If the job somehow remained QUEUED, transition it to RUNNING
            # first because the domain state machine does not allow:
            #
            #     QUEUED → FAILED
            #
            # -------------------------------------------------------------

            if job.status.value == "QUEUED":

                logger.warning(
                    "TRANSLATION JOB STILL QUEUED DURING FAILURE | "
                    "job_id=%s | "
                    "transition=QUEUED_TO_RUNNING",
                    job_id,
                )

                job.start()

            # -------------------------------------------------------------
            # Only RUNNING should normally reach this point.
            # -------------------------------------------------------------

            if job.status.value != "RUNNING":

                raise RuntimeError(
                    "Cannot mark translation job as FAILED "
                    f"from status {job.status.value}"
                )

            job.fail(
                error_message
            )

            self._job_repository.save(
                job
            )

            logger.error(
                "TRANSLATION JOB MARKED FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
            )

        except Exception:

            logger.exception(
                "UNABLE TO MARK TRANSLATION JOB AS FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
            )