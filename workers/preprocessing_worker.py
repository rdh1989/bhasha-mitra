"""
===============================================================================
BHASHA MITRA

Module:
    preprocessing_worker.py

Layer:
    Workers

Description:
    Performs background preprocessing for translation jobs.

Workflow:

    Job
      ↓
    Audio Extraction
      ↓
    AI Framework /transcript
      ↓
    transcript.json
      ↓
    Language Detection
      ↓
    Persist detected source language
      ↓
    Queue Translation Job
      ↓
    Translation Worker
===============================================================================
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.application.handlers.queue_job_handler import (
    QueueJobHandler,
)

from app.application.interfaces.job_repository import (
    JobRepository,
)

from infrastructure.ai.language_detection_client import (
    LanguageDetectionClient,
)

from infrastructure.ai.transcript_client import (
    TranscriptClient,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)

from infrastructure.media.audio_extractor import (
    AudioExtractor,
)

from workers.base_worker import BaseWorker
from workers.job_queue import JobQueue
from domain.enums.job_status import JobStatus


logger = logging.getLogger(__name__)


class PreprocessingWorker(BaseWorker):
    """
    Performs background preprocessing for translation jobs.
    """

    def __init__(
        self,
        job_queue: JobQueue[str],
        translation_queue: JobQueue[str],
        job_repository: JobRepository,
        audio_extractor: AudioExtractor,
        transcript_client: TranscriptClient,
        language_detection_client: LanguageDetectionClient,
        path_manager: PathManager,
        queue_job_handler: QueueJobHandler,
    ) -> None:

        super().__init__("preprocessing")

        self._job_queue = job_queue
        self._translation_queue = translation_queue
        self._job_repository = job_repository
        self._audio_extractor = audio_extractor
        self._transcript_client = transcript_client
        self._language_detection_client = (
            language_detection_client
        )
        self._path_manager = path_manager
        self._queue_job_handler = queue_job_handler

    # =========================================================================
    # Worker
    # =========================================================================

    def run(self) -> None:
        """
        Main preprocessing worker loop.
        """

        logger.info(
            "PREPROCESSING WORKER STARTED"
        )

        while self.is_running:

            job_id = self._job_queue.get(
                timeout=1
            )

            if job_id is None:
                continue

            logger.info(
                "JOB PICKED FROM PREPROCESSING QUEUE | "
                "job_id=%s",
                job_id,
            )

            try:

                self.process_job(
                    job_id
                )

            except Exception as exc:
                error = self._build_failure_message(exc)

                logger.exception(
                    "PREPROCESSING FAILED | "
                    "job_id=%s",
                    job_id,
                )

                self._mark_failed(
                    job_id=job_id,
                    error_message=error,
                )

            finally:

                self._job_queue.task_done()

                logger.info(
                    "PREPROCESSING QUEUE TASK COMPLETED | "
                    "job_id=%s",
                    job_id,
                )

        logger.info(
            "PREPROCESSING WORKER STOPPED"
        )

    def _build_failure_message(
        self,
        error: Exception,
    ) -> str:
        """
        Build a generic persisted error message for preprocessing failures.
        """

        message = str(error).strip()

        if message:
            return message

        return (
            "Preprocessing failed. Check application logs for detailed "
            "error information."
        )

    def _mark_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> None:
        """
        Persist FAILED status for preprocessing-stage failures.

        Preprocessing typically runs while a job is PENDING.
        """

        job = self._job_repository.get(job_id)

        if job is None:

            logger.warning(
                "CANNOT MARK PREPROCESSING FAILED | "
                "JOB NOT FOUND | "
                "job_id=%s",
                job_id,
            )

            return

        logger.error(
            "MARKING PREPROCESSING JOB FAILED | "
            "job_id=%s | "
            "current_status=%s | "
            "error=%s",
            job_id,
            job.status.value,
            error_message,
        )

        try:

            if job.status == JobStatus.PENDING:
                job.queue()
                job.start()

            elif job.status == JobStatus.QUEUED:
                job.start()

            if job.status == JobStatus.RUNNING:
                job.fail(error_message)

            elif job.status == JobStatus.FAILED:
                job.error_message = error_message
                job.updated_at = datetime.now(UTC)

            else:
                raise RuntimeError(
                    "Cannot mark preprocessing failure from "
                    f"status {job.status.value}"
                )

            self._job_repository.save(job)

            logger.error(
                "PREPROCESSING JOB MARKED FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
            )

        except Exception:

            logger.exception(
                "UNABLE TO MARK PREPROCESSING JOB AS FAILED | "
                "job_id=%s | "
                "status=%s",
                job_id,
                job.status.value,
            )

    # =========================================================================
    # Job Processing
    # =========================================================================

    def process_job(
        self,
        job_id: str,
    ) -> None:
        """
        Process background preprocessing for a job.
        """

        logger.info(
            "JOB PREPROCESSING STARTED | "
            "job_id=%s",
            job_id,
        )

        job = self._job_repository.get(
            job_id
        )

        if job is None:

            logger.warning(
                "JOB NOT FOUND | "
                "job_id=%s",
                job_id,
            )

            return

        logger.info(
            "JOB LOADED | "
            "job_id=%s | status=%s | file=%s",
            job.id,
            job.status.value,
            job.input_file,
        )

        if job.is_finished:

            logger.info(
                "JOB ALREADY FINISHED | "
                "job_id=%s",
                job.id,
            )

            return

        # =====================================================================
        # Audio Extraction
        # =====================================================================

        if not job.preprocessing.audio_extracted:

            logger.warning(
                "JOB STATUS | "
                "job_id=%s | "
                "stage=AUDIO_EXTRACTION | "
                "status=STARTED | "
                "input=%s",
                job.id,
                job.input_file,
            )

            audio_file = (
                self._audio_extractor.extract(
                    input_file=job.input_file,
                    video_name=job.input_file.name,
                    job_id=job.id,
                )
            )

            logger.info(
                "AUDIO EXTRACTION RETURNED | "
                "job_id=%s | audio=%s",
                job.id,
                audio_file,
            )

            job.mark_audio_extracted(
                audio_file
            )

            self._job_repository.save(
                job
            )

            logger.warning(
                "JOB STATUS | "
                "job_id=%s | "
                "stage=AUDIO_EXTRACTION | "
                "status=COMPLETED | "
                "audio=%s",
                job.id,
                audio_file,
            )

        else:

            logger.info(
                "AUDIO EXTRACTION ALREADY COMPLETED | "
                "job_id=%s | audio=%s",
                job.id,
                job.preprocessing.audio_file,
            )

        audio_file = (
            job.preprocessing.audio_file
        )

        if audio_file is None:

            raise RuntimeError(
                "Audio file is unavailable."
            )

        if not audio_file.is_file():

            raise FileNotFoundError(
                f"Audio file not found: {audio_file}"
            )

        # =====================================================================
        # Transcript / ASR
        # =====================================================================

        if not job.preprocessing.asr_completed:

            logger.warning(
                "JOB STATUS | "
                "job_id=%s | "
                "stage=TRANSCRIPTION | "
                "status=STARTING | "
                "audio=%s",
                job.id,
                audio_file,
            )

            transcript_file = (
                self._generate_transcript(
                    job_id=job.id,
                    video_name=job.input_file.name,
                    audio_file=audio_file,
                )
            )

            logger.warning(
                "TRANSCRIPT GENERATION RETURNED | "
                "job_id=%s | transcript=%s",
                job.id,
                transcript_file,
            )

            job.mark_asr_completed(
                transcript_file
            )

            self._job_repository.save(
                job
            )

            logger.warning(
                "JOB STATUS | "
                "job_id=%s | "
                "stage=TRANSCRIPTION | "
                "status=COMPLETED | "
                "transcript=%s",
                job.id,
                transcript_file,
            )

        else:

            logger.info(
                "TRANSCRIPT ALREADY COMPLETED | "
                "job_id=%s | "
                "transcript=%s",
                job.id,
                job.preprocessing.transcript_file,
            )

        # =====================================================================
        # Language Detection
        # =====================================================================

        transcript_file = (
            job.preprocessing.transcript_file
        )

        if transcript_file is None:

            raise RuntimeError(
                "Transcript file is unavailable "
                "after transcription."
            )

        if not transcript_file.is_file():

            raise FileNotFoundError(
                "Transcript file does not exist: "
                f"{transcript_file}"
            )

        logger.warning(
            "JOB STATUS | "
            "job_id=%s | "
            "stage=LANGUAGE_DETECTION | "
            "status=STARTING | "
            "transcript=%s",
            job.id,
            transcript_file,
        )

        detected_language = (
            self._detect_language(
                job_id=job.id,
                transcript_file=transcript_file,
            )
        )

        logger.warning(
            "LANGUAGE DETECTION COMPLETED | "
            "job_id=%s | "
            "detected_language=%s",
            job.id,
            detected_language,
        )

        # =====================================================================
        # Persist detected source language
        # =====================================================================

        logger.info(
            "UPDATING JOB SOURCE LANGUAGE | "
            "job_id=%s | "
            "previous=%s | "
            "detected=%s",
            job.id,
            job.source_language,
            detected_language,
        )

        job.source_language = detected_language

        self._job_repository.save(
            job
        )

        logger.info(
            "DETECTED SOURCE LANGUAGE PERSISTED | "
            "job_id=%s | "
            "source_language=%s",
            job.id,
            job.source_language,
        )

        # =====================================================================
        # Preprocessing completed
        # =====================================================================

        logger.warning(
            "JOB STATUS | "
            "job_id=%s | "
            "stage=PREPROCESSING | "
            "status=COMPLETED | "
            "source_language=%s",
            job.id,
            detected_language,
        )

        # =====================================================================
        # Queue Translation
        # =====================================================================

        self._queue_translation_job(
            job.id
        )

        logger.info(
            "JOB PREPROCESSING FINISHED | "
            "job_id=%s | "
            "NEXT_STAGE=TRANSLATION",
            job.id,
        )

    # =========================================================================
    # Translation Handoff
    # =========================================================================

    def _queue_translation_job(
        self,
        job_id: str,
    ) -> None:
        """
        Transition the job to QUEUED and place it
        into the translation queue.

        Required lifecycle:

            PENDING
                ↓
            QUEUED
                ↓
            translation_queue
                ↓
            TranslationWorker
                ↓
            RUNNING
        """

        logger.warning(
            "TRANSLATION QUEUE REQUESTED | "
            "job_id=%s",
            job_id,
        )

        # ---------------------------------------------------------------------
        # Reload latest persisted job
        # ---------------------------------------------------------------------

        job = self._job_repository.get(
            job_id
        )

        if job is None:

            raise RuntimeError(
                "Unable to queue translation job. "
                f"Job not found: {job_id}"
            )

        logger.info(
            "TRANSLATION QUEUE JOB LOADED | "
            "job_id=%s | current_status=%s",
            job.id,
            job.status.value,
        )

        # ---------------------------------------------------------------------
        # Transition domain state
        # ---------------------------------------------------------------------

        if not job.is_queued:

            logger.warning(
                "TRANSLATION JOB STATE TRANSITION REQUESTED | "
                "job_id=%s | "
                "from=%s | "
                "to=QUEUED",
                job.id,
                job.status.value,
            )

            queued_job = (
                self._queue_job_handler.handle(
                    job.id
                )
            )

            if queued_job is None:

                raise RuntimeError(
                    "QueueJobHandler could not find job: "
                    f"{job.id}"
                )

            job = queued_job

            logger.warning(
                "TRANSLATION JOB STATE TRANSITIONED | "
                "job_id=%s | "
                "status=%s",
                job.id,
                job.status.value,
            )

        else:

            logger.info(
                "TRANSLATION JOB ALREADY QUEUED | "
                "job_id=%s",
                job.id,
            )

        # ---------------------------------------------------------------------
        # Verify domain state before queueing
        # ---------------------------------------------------------------------

        if not job.is_queued:

            raise RuntimeError(
                "Translation job was not moved to "
                f"QUEUED state: {job.id}"
            )

        logger.info(
            "TRANSLATION JOB STATE VERIFIED | "
            "job_id=%s | "
            "status=%s",
            job.id,
            job.status.value,
        )

        # ---------------------------------------------------------------------
        # Put job into translation queue
        # ---------------------------------------------------------------------

        logger.warning(
            "PUTTING JOB INTO TRANSLATION QUEUE | "
            "job_id=%s",
            job.id,
        )

        self._translation_queue.put(
            job.id
        )

        logger.warning(
            "JOB QUEUED FOR TRANSLATION | "
            "job_id=%s | "
            "status=%s | "
            "source_language=%s | "
            "target_language=%s",
            job.id,
            job.status.value,
            job.source_language,
            job.target_language,
        )

    # =========================================================================
    # Language Detection
    # =========================================================================

    def _detect_language(
        self,
        job_id: str,
        transcript_file: Path,
    ) -> str:
        """
        Detect source language from generated transcript.
        """

        logger.info(
            "LANGUAGE DETECTION REQUEST STARTED | "
            "job_id=%s | transcript=%s",
            job_id,
            transcript_file,
        )

        # ---------------------------------------------------------------------
        # Read transcript JSON
        # ---------------------------------------------------------------------

        try:

            with transcript_file.open(
                "r",
                encoding="utf-8",
            ) as file:

                transcript_data = json.load(
                    file
                )

        except Exception as exc:

            logger.exception(
                "TRANSCRIPT JSON READ FAILED | "
                "job_id=%s | "
                "transcript=%s | "
                "error_type=%s | "
                "error=%s",
                job_id,
                transcript_file,
                type(exc).__name__,
                exc,
            )

            raise RuntimeError(
                "Unable to read transcript JSON."
            ) from exc

        # ---------------------------------------------------------------------
        # Extract transcript text
        # ---------------------------------------------------------------------

        transcript_text = (
            transcript_data.get(
                "transcript"
            )
        )

        if not isinstance(
            transcript_text,
            str,
        ) or not transcript_text.strip():

            logger.error(
                "TRANSCRIPT TEXT MISSING | "
                "job_id=%s | "
                "transcript=%s",
                job_id,
                transcript_file,
            )

            raise RuntimeError(
                "Transcript JSON does not contain "
                "valid transcript text."
            )

        logger.info(
            "TRANSCRIPT TEXT READY FOR LANGUAGE DETECTION | "
            "job_id=%s | "
            "characters=%d",
            job_id,
            len(transcript_text),
        )

        # ---------------------------------------------------------------------
        # AI Language Detection
        # ---------------------------------------------------------------------

        try:

            result = (
                self._language_detection_client.detect(
                    text=transcript_text,
                )
            )

        except Exception:

            logger.exception(
                "LANGUAGE DETECTION API FAILED | "
                "job_id=%s | "
                "transcript=%s",
                job_id,
                transcript_file,
            )

            raise

        logger.info(
            "LANGUAGE DETECTION API RESPONSE RECEIVED | "
            "job_id=%s | "
            "result_type=%s | "
            "result=%s",
            job_id,
            type(result).__name__,
            result,
        )

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Language detection API returned "
                "an invalid response."
            )

        # ---------------------------------------------------------------------
        # Support common response field names
        # ---------------------------------------------------------------------

        detected_language = (
            result.get("language")
            or result.get("detected_language")
            or result.get("language_code")
        )

        if not detected_language:

            logger.error(
                "DETECTED LANGUAGE MISSING | "
                "job_id=%s | response=%s",
                job_id,
                result,
            )

            raise RuntimeError(
                "Language detection API did not return "
                "a detected language."
            )

        detected_language = str(
            detected_language
        ).strip()

        if not detected_language:

            raise RuntimeError(
                "Detected language is empty."
            )

        logger.warning(
            "SOURCE LANGUAGE DETECTED | "
            "job_id=%s | "
            "language=%s",
            job_id,
            detected_language,
        )

        return detected_language

    # =========================================================================
    # Transcript
    # =========================================================================

    def _generate_transcript(
        self,
        job_id: str,
        video_name: str,
        audio_file: Path,
    ) -> Path:
        """
        Generate transcript using the AI Framework.
        """

        logger.warning(
            "TRANSCRIPTION STARTED | "
            "job_id=%s | "
            "audio=%s",
            job_id,
            audio_file,
        )

        stop_progress = threading.Event()

        def log_progress() -> None:

            logger.warning(
                "TRANSCRIPTION MONITOR STARTED | "
                "job_id=%s | "
                "interval=50s",
                job_id,
            )

            elapsed = 0

            while True:

                stopped = stop_progress.wait(
                    timeout=50
                )

                if stopped:
                    break

                elapsed += 50

                logger.warning(
                    "JOB STATUS | "
                    "job_id=%s | "
                    "stage=TRANSCRIPTION | "
                    "status=IN_PROGRESS | "
                    "elapsed=%ss | "
                    "message=ASR transcription is still running",
                    job_id,
                    elapsed,
                )

        progress_thread = threading.Thread(
            target=log_progress,
            name=f"TranscriptProgress-{job_id[:8]}",
            daemon=True,
        )

        progress_thread.start()

        logger.warning(
            "TRANSCRIPTION MONITOR THREAD STARTED | "
            "job_id=%s | alive=%s",
            job_id,
            progress_thread.is_alive(),
        )

        result = None

        try:

            logger.warning(
                "AI TRANSCRIPT REQUEST STARTED | "
                "job_id=%s | "
                "audio=%s",
                job_id,
                audio_file,
            )

            result = (
                self._transcript_client.generate(
                    audio_path=str(
                        audio_file
                    ),
                )
            )

            logger.warning(
                "AI TRANSCRIPT RESPONSE RECEIVED | "
                "job_id=%s | "
                "result_type=%s",
                job_id,
                type(result).__name__,
            )

        except Exception:

            logger.exception(
                "AI TRANSCRIPT REQUEST FAILED | "
                "job_id=%s | "
                "audio=%s",
                job_id,
                audio_file,
            )

            raise

        finally:

            logger.warning(
                "STOPPING TRANSCRIPTION MONITOR | "
                "job_id=%s",
                job_id,
            )

            stop_progress.set()

            progress_thread.join(
                timeout=2.0
            )

            logger.warning(
                "TRANSCRIPTION MONITOR JOINED | "
                "job_id=%s | alive=%s",
                job_id,
                progress_thread.is_alive(),
            )

        # =====================================================================
        # Validate response
        # =====================================================================

        logger.info(
            "VALIDATING AI TRANSCRIPT RESPONSE | "
            "job_id=%s",
            job_id,
        )

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "AI Transcript API returned "
                "an invalid response."
            )

        if result.get("status") != "PASS":

            raise RuntimeError(
                "AI Transcript API did not return PASS status."
            )

        transcript_path = result.get(
            "transcript_path"
        )

        if not transcript_path:

            raise RuntimeError(
                "AI Transcript API did not return "
                "a transcript_path."
            )

        transcript_file = (
            Path(
                transcript_path
            )
            .expanduser()
            .resolve()
        )

        if not transcript_file.exists():

            raise FileNotFoundError(
                "AI Transcript API returned a transcript "
                f"path that does not exist: {transcript_file}"
            )

        if not transcript_file.is_file():

            raise RuntimeError(
                "AI Transcript API returned a transcript "
                f"path that is not a file: {transcript_file}"
            )

        logger.info(
            "TRANSCRIPT FILE VALIDATED | "
            "job_id=%s | "
            "transcript=%s | "
            "size=%d bytes",
            job_id,
            transcript_file,
            transcript_file.stat().st_size,
        )

        logger.warning(
            "TRANSCRIPT READY | "
            "job_id=%s | "
            "path=%s | "
            "size=%d bytes",
            job_id,
            transcript_file,
            transcript_file.stat().st_size,
        )

        return transcript_file