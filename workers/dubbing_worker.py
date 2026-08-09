"""
BHASHA MITRA

Module:
dubbing_worker.py

Layer:
Workers

Description:
Executes the dubbing stage after translation.

Workflow:

    Translation
        ↓
    translation.json
        ↓
    Dubbing Queue
        ↓
    Dubbing Worker
        ↓
    AI Framework /dubbing
        ↓
    Dubbed Audio

The AI Framework owns:
- TTS
- Voice generation
- Dubbed audio generation

The Backend owns:
- Queue processing
- Workflow invocation
- Artifact persistence
- Error logging
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

from infrastructure.ai.dubbing_client import (
    DubbingClient,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue


logger = logging.getLogger(__name__)


class DubbingWorker(BaseWorker):
    """
    Executes the dubbing stage.
    """

    # =========================================================================
    # Windows file-lock protection
    # =========================================================================

    DUBBING_COPY_RETRIES = 30
    DUBBING_COPY_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        job_queue: JobQueue[str],
        job_repository: JobRepository,
        dubbing_client: DubbingClient,
        path_manager: PathManager,
        voice: str,
    ) -> None:

        super().__init__("dubbing")

        self._job_queue = job_queue
        self._job_repository = job_repository
        self._dubbing_client = dubbing_client
        self._path_manager = path_manager
        self._voice = voice

    # =========================================================================
    # Background worker
    # =========================================================================

    def run(self) -> None:
        """
        Process queued dubbing jobs.
        """

        logger.info(
            "DUBBING WORKER STARTED"
        )

        while self.is_running:

            job_id = self._job_queue.get(
                timeout=1
            )

            if job_id is None:
                continue

            logger.info(
                "DUBBING JOB PICKED FROM QUEUE | "
                "job_id=%s",
                job_id,
            )

            try:

                job = self._job_repository.get(
                    job_id
                )

                if job is None:

                    logger.warning(
                        "DUBBING JOB NOT FOUND | "
                        "job_id=%s",
                        job_id,
                    )

                    continue

                self.execute(job)

            except Exception as exc:

                logger.exception(
                    "DUBBING FAILED | "
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
                    "DUBBING QUEUE TASK COMPLETED | "
                    "job_id=%s",
                    job_id,
                )

        logger.info(
            "DUBBING WORKER STOPPED"
        )

    # =========================================================================
    # Dubbing
    # =========================================================================

    def execute(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute dubbing after translation.
        """

        logger.warning(
            "JOB STATUS | "
            "job_id=%s | "
            "stage=DUBBING | "
            "status=STARTING",
            job.id,
        )

        # =====================================================================
        # Translation Preconditions
        # =====================================================================

        transcript_file = (
            job.preprocessing.transcript_file
        )

        if transcript_file is None:

            raise RuntimeError(
                "Transcript file is not available "
                "for dubbing."
            )

        if not transcript_file.is_file():

            raise FileNotFoundError(
                "Transcript file does not exist: "
                f"{transcript_file}"
            )

        # =====================================================================
        # Translation Artifact
        # =====================================================================

        # The transcript artifact already resides in this job's
        # canonical `files` directory. Use its parent rather than
        # reconstructing the directory through job_directory(), which
        # requires video_name as well as job_id.
        job_files_directory = transcript_file.parent

        translation_file = (
            job_files_directory
            / "translation.json"
        )

        if not translation_file.is_file():

            raise FileNotFoundError(
                "Translation file does not exist: "
                f"{translation_file}"
            )

        logger.info(
            "DUBBING INPUT READY | "
            "job_id=%s | "
            "translation=%s | "
            "language=%s | "
            "voice=%s",
            job.id,
            translation_file,
            job.target_language,
            self._voice,
        )

        # =====================================================================
        # Call AI Framework
        # =====================================================================

        logger.warning(
            "DUBBING REQUEST STARTED | "
            "job_id=%s | "
            "translation=%s | "
            "language=%s | "
            "voice=%s",
            job.id,
            translation_file,
            job.target_language,
            self._voice,
        )

        # Backend owns the final artifact location and provides it to
        # the AI Framework. The AI Framework writes the dubbed audio
        # directly to this path.
        dubbing_file = (
            job_files_directory
            / "dubbed_audio.wav"
        )

        result = self._dubbing_client.generate(
            translated_text_path=str(
                translation_file
            ),
            language=job.target_language,
            voice=self._voice,
            output_path=str(dubbing_file),
        )

        logger.info(
            "DUBBING API RESPONSE RECEIVED | "
            "job_id=%s | "
            "result_type=%s",
            job.id,
            type(result).__name__,
        )

        # =====================================================================
        # Validate Response
        # =====================================================================

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Dubbing API returned an invalid response."
            )

        # VideoDubbingResult uses `audio_file` as its canonical output field.
        # Keep the legacy aliases for provider/API compatibility.
        returned_audio_path = (
            result.get("audio_file")
            or result.get("dubbing_path")
            or result.get("audio_path")
            or result.get("output_path")
        )

        # The backend supplied output_path to the AI Framework. Prefer that
        # path because it is the canonical backend artifact location.
        expected_output = dubbing_file

        if returned_audio_path:
            returned_audio = (
                Path(str(returned_audio_path))
                .expanduser()
                .resolve()
            )

            # If the AI Framework reports a different path, use it only when
            # the requested backend output was not created. This preserves
            # compatibility without blindly copying a locked source file.
            if (
                not expected_output.is_file()
                and returned_audio.is_file()
            ):
                logger.info(
                    "DUBBING API RETURNED ALTERNATE AUDIO PATH | "
                    "job_id=%s | "
                    "audio=%s",
                    job.id,
                    returned_audio,
                )

                self._copy_dubbing_artifact(
                    source=returned_audio,
                    destination=expected_output,
                    job_id=job.id,
                )

        if not expected_output.is_file():

            if returned_audio_path:
                raise FileNotFoundError(
                    "Dubbing API returned an audio path, but the "
                    "expected backend output was not created: "
                    f"{expected_output}"
                )

            raise FileNotFoundError(
                "Dubbing API completed without creating the expected "
                f"audio artifact: {expected_output}"
            )

        logger.info(
            "DUBBING API RESPONSE RECEIVED | "
            "job_id=%s | "
            "result_type=%s | "
            "audio=%s",
            job.id,
            type(result).__name__,
            expected_output,
        )

        # =====================================================================
        # Final Artifact
        # =====================================================================

        # No copy is required when the AI Framework writes directly to the
        # backend-owned output_path. This avoids Windows WinError 32 caused
        # by copying an AI-generated file that is still open.
        dubbing_file = expected_output

        logger.info(
            "DUBBING ARTIFACT READY | "
            "job_id=%s | "
            "audio=%s",
            job.id,
            dubbing_file,
        )

        # =====================================================================
        # Completed
        # =====================================================================

        logger.warning(
            "JOB STATUS | "
            "job_id=%s | "
            "stage=DUBBING | "
            "status=COMPLETED | "
            "audio=%s",
            job.id,
            dubbing_file,
        )

        logger.info(
            "DUBBING COMPLETED | "
            "job_id=%s | "
            "audio=%s",
            job.id,
            dubbing_file,
        )

    # =========================================================================
    # Windows-safe artifact copy
    # =========================================================================

    def _copy_dubbing_artifact(
        self,
        source: Path,
        destination: Path,
        job_id: str,
    ) -> None:
        """
        Copy the AI-generated dubbed audio safely on Windows.

        WinError 32 is retried because the AI Framework may briefly retain
        a file handle after generating the audio artifact.

        Other PermissionError values are raised immediately.
        """

        last_error: PermissionError | None = None

        for attempt in range(
            1,
            self.DUBBING_COPY_RETRIES + 1,
        ):

            try:

                logger.info(
                    "DUBBING ARTIFACT COPY ATTEMPT | "
                    "job_id=%s | "
                    "attempt=%d/%d | "
                    "source=%s | "
                    "destination=%s",
                    job_id,
                    attempt,
                    self.DUBBING_COPY_RETRIES,
                    source,
                    destination,
                )

                shutil.copy2(
                    source,
                    destination,
                )

                logger.info(
                    "DUBBING ARTIFACT COPY SUCCEEDED | "
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

                if getattr(
                    exc,
                    "winerror",
                    None,
                ) != 32:

                    raise

                if attempt >= self.DUBBING_COPY_RETRIES:

                    logger.error(
                        "DUBBING ARTIFACT COPY FAILED - "
                        "SOURCE REMAINS LOCKED | "
                        "job_id=%s | "
                        "attempts=%d | "
                        "source=%s | "
                        "destination=%s",
                        job_id,
                        self.DUBBING_COPY_RETRIES,
                        source,
                        destination,
                    )

                    raise

                logger.warning(
                    "DUBBING ARTIFACT SOURCE LOCKED | "
                    "job_id=%s | "
                    "attempt=%d/%d | "
                    "retry_in=%.1fs | "
                    "source=%s",
                    job_id,
                    attempt,
                    self.DUBBING_COPY_RETRIES,
                    self.DUBBING_COPY_RETRY_DELAY_SECONDS,
                    source,
                )

                time.sleep(
                    self.DUBBING_COPY_RETRY_DELAY_SECONDS
                )

        # Defensive guard. The loop either returns or raises.
        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Dubbed audio artifact copy failed unexpectedly."
        )