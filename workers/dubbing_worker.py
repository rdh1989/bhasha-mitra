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

from datetime import UTC, datetime
import json
import logging
import shutil
import time
from pathlib import Path

from app.application.interfaces.job_repository import (
    JobRepository,
)

from domain.entities import TranslationJob
from domain.enums.job_status import JobStatus

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
    TIMESTAMP_EPSILON_SECONDS = 0.001
    MIN_SEGMENT_DURATION_SECONDS = 0.05

    def __init__(
        self,
        job_queue: JobQueue[str],
        export_queue: JobQueue[str],
        job_repository: JobRepository,
        dubbing_client: DubbingClient,
        path_manager: PathManager,
        voice: str,
    ) -> None:

        super().__init__("dubbing")

        self._job_queue = job_queue
        self._export_queue = export_queue
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

                self._mark_failed(
                    job_id=job_id,
                    error_message=self._build_failure_message(exc),
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

        normalized_translation_file = (
            self._normalize_translation_timestamps(
                translation_file=translation_file,
                job_id=job.id,
            )
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
            normalized_translation_file,
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
                normalized_translation_file
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

        # =====================================================================
        # Queue Export
        # =====================================================================

        logger.warning(
            "EXPORT QUEUE REQUESTED | "
            "job_id=%s | "
            "audio=%s",
            job.id,
            dubbing_file,
        )

        self._export_queue.put(
            job.id
        )

        logger.warning(
            "JOB QUEUED FOR EXPORT | "
            "job_id=%s",
            job.id,
        )

    def _normalize_translation_timestamps(
        self,
        translation_file: Path,
        job_id: str,
    ) -> Path:
        """
        Normalize translation segment timeline to avoid overlaps.

        The AI dubbing pipeline rejects overlapping segments. This step
        preserves ordering and text while repairing start/end boundaries.
        """

        with translation_file.open(
            "r",
            encoding="utf-8",
        ) as handle:

            payload = json.load(handle)

        segments = payload.get("segments")

        if not isinstance(segments, list) or not segments:
            return translation_file

        normalized_segments: list[dict] = []
        previous_end = 0.0
        adjusted_count = 0

        for index, segment in enumerate(segments, start=1):

            if not isinstance(segment, dict):
                normalized_segments.append(segment)
                continue

            start_raw = segment.get("start")
            end_raw = segment.get("end")

            try:
                start = float(start_raw)
                end = float(end_raw)
            except (TypeError, ValueError):
                normalized_segments.append(segment)
                continue

            original_start = start
            original_end = end

            # Ensure monotonically non-decreasing start times.
            if start < previous_end:
                start = previous_end

            # Ensure positive segment duration.
            if end <= start:
                end = start + self.MIN_SEGMENT_DURATION_SECONDS

            if (
                abs(start - original_start) > self.TIMESTAMP_EPSILON_SECONDS
                or abs(end - original_end) > self.TIMESTAMP_EPSILON_SECONDS
            ):
                adjusted_count += 1

            normalized_segment = dict(segment)
            normalized_segment["start"] = round(start, 3)
            normalized_segment["end"] = round(end, 3)

            normalized_segments.append(normalized_segment)
            previous_end = end

            logger.debug(
                "DUBBING TIMELINE SEGMENT CHECK | "
                "job_id=%s | "
                "index=%s | "
                "start=%s | "
                "end=%s",
                job_id,
                index,
                normalized_segment["start"],
                normalized_segment["end"],
            )

        if adjusted_count == 0:

            return translation_file

        normalized_payload = dict(payload)
        normalized_payload["segments"] = normalized_segments

        normalized_path = (
            translation_file.parent
            / "translation_dubbing_normalized.json"
        )

        with normalized_path.open(
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                normalized_payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

        logger.warning(
            "DUBBING TIMELINE NORMALIZED | "
            "job_id=%s | "
            "source=%s | "
            "normalized=%s | "
            "adjusted_segments=%s",
            job_id,
            translation_file,
            normalized_path,
            adjusted_count,
        )

        return normalized_path

    # =========================================================================
    # Failure handling
    # =========================================================================

    def _build_failure_message(
        self,
        error: Exception,
    ) -> str:
        """
        Convert worker/runtime exceptions into concise persisted messages.
        """

        message = str(error).strip()

        if message:
            return message

        return (
            "Dubbing failed due to an unexpected error. "
            "Check worker logs for details."
        )

    def _mark_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> None:
        """
        Persist FAILED status for a dubbing-stage failure.

        Dubbing currently runs after translation marks the job COMPLETED.
        This method supports both RUNNING and COMPLETED as recoverable
        failure sources so UI and history reflect real pipeline outcome.
        """

        job = self._job_repository.get(
            job_id
        )

        if job is None:

            logger.warning(
                "CANNOT MARK DUBBING FAILED | "
                "JOB NOT FOUND | "
                "job_id=%s",
                job_id,
            )

            return

        logger.error(
            "MARKING DUBBING JOB FAILED | "
            "job_id=%s | "
            "current_status=%s | "
            "error=%s",
            job_id,
            job.status.value,
            error_message,
        )

        try:

            if job.status == JobStatus.QUEUED:

                logger.warning(
                    "DUBBING FAILURE ON QUEUED JOB | "
                    "job_id=%s | "
                    "transition=QUEUED_TO_RUNNING",
                    job_id,
                )

                job.start()

            if job.status == JobStatus.RUNNING:

                job.fail(
                    error_message
                )

            elif job.status == JobStatus.COMPLETED:

                now = datetime.now(UTC)

                job.status = JobStatus.FAILED
                job.error_message = error_message
                job.completed_at = now
                job.updated_at = now

            elif job.status == JobStatus.FAILED:

                job.error_message = error_message
                job.updated_at = datetime.now(UTC)

            else:

                raise RuntimeError(
                    "Cannot mark dubbing failure from "
                    f"status {job.status.value}"
                )

            self._job_repository.save(
                job
            )

            logger.error(
                "DUBBING JOB MARKED FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
            )

            logger.warning(
                "JOB STATUS | "
                "job_id=%s | "
                "stage=DUBBING | "
                "status=FAILED | "
                "error=%s",
                job_id,
                error_message,
            )

        except Exception:

            logger.exception(
                "UNABLE TO MARK DUBBING JOB AS FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
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