"""
BHASHA MITRA

Module:
    infrastructure/bootstrap/application_container.py

Layer:
    Infrastructure / Bootstrap

Description:
    Creates and wires shared application dependencies.

Responsibilities:
    - Configuration
    - Repository
    - Application services
    - Job queues
    - AI Framework clients
    - Media services
    - Background workers
    - Workflow dependencies
"""

from __future__ import annotations

from pathlib import Path

from app.application.handlers.cancel_job_handler import (
    CancelJobHandler,
)
from app.application.handlers.complete_job_handler import (
    CompleteJobHandler,
)
from app.application.handlers.create_job_handler import (
    CreateJobHandler,
)
from app.application.handlers.delete_job_handler import (
    DeleteJobHandler,
)
from app.application.handlers.fail_job_handler import (
    FailJobHandler,
)
from app.application.handlers.get_job_handler import (
    GetJobHandler,
)
from app.application.handlers.list_jobs_handler import (
    ListJobsHandler,
)
from app.application.handlers.queue_job_handler import (
    QueueJobHandler,
)
from app.application.handlers.retry_job_handler import (
    RetryJobHandler,
)
from app.application.handlers.start_job_handler import (
    StartJobHandler,
)
from app.application.handlers.update_progress_handler import (
    UpdateProgressHandler,
)

from app.application.services.job_service import (
    JobService,
)

from app.application.validators.job_validator import (
    JobValidator,
)

from infrastructure.ai.dubbing_client import (
    DubbingClient,
)

from infrastructure.ai.language_detection_client import (
    LanguageDetectionClient,
)

from infrastructure.ai.transcript_client import (
    TranscriptClient,
)

from infrastructure.ai.translation_client import (
    TranslationClient,
)

from infrastructure.configuration.configuration_manager import (
    ConfigurationManager,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)

from infrastructure.media.audio_extractor import (
    AudioExtractor,
)

from infrastructure.persistence.job.sqlite_job_repository import (
    SQLiteJobRepository,
)

from workers.job_queue import JobQueue
from workers.preprocessing_worker import (
    PreprocessingWorker,
)
from workers.translation_worker import (
    TranslationWorker,
)
from workers.dubbing_worker import (
    DubbingWorker,
)


class ApplicationContainer:
    """
    Creates and owns shared application dependencies.
    """

    def __init__(self) -> None:

        # =================================================================
        # Configuration
        # =================================================================

        self.configuration = ConfigurationManager()

        self.configuration.initialize()

        # =================================================================
        # Filesystem
        # =================================================================

        self.path_manager = PathManager()

        # =================================================================
        # Repository
        # =================================================================

        self.job_repository = SQLiteJobRepository(
            self.path_manager.database_path
        )

        # =================================================================
        # Validator
        # =================================================================

        self.job_validator = JobValidator(
            job_repository=self.job_repository,
            configuration_manager=self.configuration,
        )

        # =================================================================
        # Job Handlers
        # =================================================================

        self.create_job_handler = CreateJobHandler(
            validator=self.job_validator,
            job_repository=self.job_repository,
        )

        self.get_job_handler = GetJobHandler(
            job_repository=self.job_repository,
        )

        self.list_jobs_handler = ListJobsHandler(
            job_repository=self.job_repository,
        )

        self.delete_job_handler = DeleteJobHandler(
            job_repository=self.job_repository,
        )

        self.queue_job_handler = QueueJobHandler(
            job_repository=self.job_repository,
        )

        self.start_job_handler = StartJobHandler(
            job_repository=self.job_repository,
        )

        self.complete_job_handler = CompleteJobHandler(
            job_repository=self.job_repository,
        )

        self.fail_job_handler = FailJobHandler(
            job_repository=self.job_repository,
        )

        self.retry_job_handler = RetryJobHandler(
            job_repository=self.job_repository,
        )

        self.cancel_job_handler = CancelJobHandler(
            job_repository=self.job_repository,
        )

        self.update_progress_handler = UpdateProgressHandler(
            job_repository=self.job_repository,
        )

        # =================================================================
        # Job Service
        # =================================================================

        self.job_service = JobService(
            create_handler=self.create_job_handler,
            get_handler=self.get_job_handler,
            list_handler=self.list_jobs_handler,
            delete_handler=self.delete_job_handler,
            queue_handler=self.queue_job_handler,
            start_handler=self.start_job_handler,
            complete_handler=self.complete_job_handler,
            fail_handler=self.fail_job_handler,
            retry_handler=self.retry_job_handler,
            cancel_handler=self.cancel_job_handler,
            update_progress_handler=self.update_progress_handler,
        )

        # =================================================================
        # Queues
        # =================================================================

        self.preprocessing_queue: JobQueue[str] = JobQueue()

        self.translation_queue: JobQueue[str] = JobQueue()

        self.dubbing_queue: JobQueue[str] = JobQueue()

        # =================================================================
        # FFmpeg
        # =================================================================

        ffmpeg_directory = (
            self._get_ffmpeg_directory()
        )

        ffmpeg_executable = (
            ffmpeg_directory / "ffmpeg.exe"
        )

        self.audio_extractor = AudioExtractor(
            ffmpeg_path=ffmpeg_executable,
            path_manager=self.path_manager,
        )

        # =================================================================
        # AI Framework Base URL
        # =================================================================

        ai_base_url = (
            self.configuration.get_value(
                "app",
                "ai_base_url",
            )
        )

        if not ai_base_url:

            raise RuntimeError(
                "AI Framework base URL is not configured."
            )

        # =================================================================
        # AI Framework Clients
        # =================================================================

        self.transcript_client = TranscriptClient(
            base_url=ai_base_url,
        )

        self.language_detection_client = (
            LanguageDetectionClient(
                base_url=ai_base_url,
            )
        )

        self.translation_client = TranslationClient(
            base_url=ai_base_url,
        )

        self.dubbing_client = DubbingClient(
            base_url=ai_base_url,
        )

        # =================================================================
        # Preprocessing Worker
        # =================================================================
        #
        # Workflow:
        #
        #   Audio Extraction
        #        ↓
        #   Transcription
        #        ↓
        #   Language Detection
        #        ↓
        #   PENDING → QUEUED
        #        ↓
        #   Translation Queue
        #
        # queue_job_handler performs:
        #
        #   PENDING → QUEUED
        #
        # before the job is placed into translation_queue.
        # =================================================================

        self.preprocessing_worker = (
            PreprocessingWorker(
                job_queue=self.preprocessing_queue,
                translation_queue=self.translation_queue,
                job_repository=self.job_repository,
                audio_extractor=self.audio_extractor,
                transcript_client=self.transcript_client,
                language_detection_client=(
                    self.language_detection_client
                ),
                path_manager=self.path_manager,
                queue_job_handler=(
                    self.queue_job_handler
                ),
            )
        )

        # =================================================================
        # Translation Worker
        # =================================================================
        #
        # Workflow:
        #
        #   Translation Queue
        #        ↓
        #   QUEUED → RUNNING
        #        ↓
        #   AI Translation
        #        ↓
        #   translation.json
        #        ↓
        #   RUNNING → COMPLETED
        #        ↓
        #   Dubbing Queue
        # =================================================================

        self.translation_worker = (
            TranslationWorker(
                job_queue=self.translation_queue,
                dubbing_queue=self.dubbing_queue,
                job_repository=self.job_repository,
                translation_client=self.translation_client,
                path_manager=self.path_manager,
            )
        )

        # =================================================================
        # Dubbing Worker
        # =================================================================
        #
        # Workflow:
        #
        #   Dubbing Queue
        #        ↓
        #   DubbingWorker
        #        ↓
        #   AI /dubbing
        #        ↓
        #   dubbed audio artifact
        #
        # DubbingWorker requires a voice.
        #
        # Current Bhasha Mitra default Marathi voice:
        #   mr_IN-google-medium
        #
        # This can later be moved to ConfigurationManager when voice
        # selection becomes configurable.
        # =================================================================

        dubbing_voice = "mr_IN-google-medium"

        self.dubbing_worker = (
            DubbingWorker(
                job_queue=self.dubbing_queue,
                job_repository=self.job_repository,
                dubbing_client=self.dubbing_client,
                path_manager=self.path_manager,
                voice=dubbing_voice,
            )
        )

    # =========================================================================
    # FFmpeg
    # =========================================================================

    def _get_ffmpeg_directory(
        self,
    ) -> Path:
        """
        Resolve FFmpeg directory from the runtime manifest.
        """

        manifest = (
            self.configuration.manifest
        )

        ffmpeg_config = manifest.get(
            "ffmpeg"
        )

        if not isinstance(
            ffmpeg_config,
            dict,
        ):

            raise RuntimeError(
                "FFmpeg configuration is missing "
                "from manifest."
            )

        ffmpeg_path = (
            ffmpeg_config.get(
                "path"
            )
        )

        if not ffmpeg_path:

            raise RuntimeError(
                "FFmpeg path is not configured "
                "in manifest."
            )

        ffmpeg_directory = Path(ffmpeg_path).expanduser()

        if not ffmpeg_directory.is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            ffmpeg_directory = (
                project_root / ffmpeg_directory
            ).resolve()

        return ffmpeg_directory.resolve()