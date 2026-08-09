"""
===============================================================================
BHASHA MITRA
SQLite Job Repository
===============================================================================

Description:
    SQLite-based persistence implementation for TranslationJob.

Responsibilities:
    - Persist translation jobs
    - Retrieve jobs by ID
    - Delete jobs
    - Check job existence
    - List jobs
    - Find active jobs
    - Persist preprocessing state
    - Persist generated artifact paths

SQLite stores:
    - Job metadata
    - Job state
    - Progress
    - Preprocessing state
    - Generated artifact paths

Filesystem stores:
    - Original video reference
    - Transcript
    - Translation
    - Subtitle text
    - SRT
    - Translated video
    - Metadata file

Configuration:
    database_path represents the database directory.

Example:
    F:/bhashamitra/database/

The SQLite database file is created inside that directory.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from app.application.interfaces.job_repository import (
    JobRepository,
)

from domain.entities import TranslationJob
from domain.enums.job_priority import JobPriority
from domain.enums.job_status import JobStatus
from domain.value_objects.job_progress import JobProgress
from domain.value_objects.preprocessing_state import (
    PreprocessingState,
)


logger = logging.getLogger(__name__)


class SQLiteJobRepository(JobRepository):
    """
    SQLite implementation of JobRepository.
    """

    DATABASE_FILENAME = "bhasha_mitra.db"

    def __init__(
        self,
        database_path: Path,
    ) -> None:

        # =====================================================================
        # Configured database directory
        # =====================================================================

        self._database_directory = (
            Path(database_path)
            .expanduser()
            .resolve()
        )

        # =====================================================================
        # SQLite database file
        # =====================================================================

        self._database_path = (
            self._database_directory
            / self.DATABASE_FILENAME
        )

        # =====================================================================
        # Prepare database directory
        # =====================================================================

        self._ensure_database_directory()

        # =====================================================================
        # Initialize database
        # =====================================================================

        self._initialize_database()

        logger.info(
            "SQLite job repository initialized | "
            "directory=%s | database=%s",
            self._database_directory,
            self._database_path,
        )

    # =========================================================================
    # Database directory
    # =========================================================================

    def _ensure_database_directory(self) -> None:
        """
        Create the configured database directory if required.
        """

        try:

            self._database_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        except OSError as exc:

            logger.exception(
                "Unable to create database directory | "
                "directory=%s",
                self._database_directory,
            )

            raise RuntimeError(
                "Unable to create configured database directory: "
                f"{self._database_directory}"
            ) from exc

        if not self._database_directory.is_dir():

            raise RuntimeError(
                "Configured database path is not a directory: "
                f"{self._database_directory}"
            )

    # =========================================================================
    # Database connection
    # =========================================================================

    def _connect(self) -> sqlite3.Connection:
        """
        Create a SQLite connection.

        SQLite creates the database file automatically if it does
        not already exist.
        """

        connection = sqlite3.connect(
            self._database_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    # =========================================================================
    # Database initialization
    # =========================================================================

    def _initialize_database(self) -> None:
        """
        Create the SQLite database and jobs table if required.
        """

        try:

            with self._connect() as connection:

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS translation_jobs (
                        id TEXT PRIMARY KEY,
                        input_file TEXT NOT NULL,
                        source_language TEXT,
                        target_language TEXT,
                        priority INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        progress TEXT NOT NULL,
                        preprocessing TEXT NOT NULL,
                        retry_count INTEGER NOT NULL,
                        output_file TEXT,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        cancelled_at TEXT,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                connection.commit()

        except sqlite3.Error as exc:

            logger.exception(
                "Unable to initialize SQLite database | "
                "database=%s",
                self._database_path,
            )

            raise RuntimeError(
                "Unable to initialize SQLite database: "
                f"{self._database_path}"
            ) from exc

        if not self._database_path.is_file():

            raise RuntimeError(
                "SQLite database file was not created: "
                f"{self._database_path}"
            )

    # =========================================================================
    # Repository
    # =========================================================================

    def save(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Insert or update a translation job.
        """

        data = job.to_dict()

        try:

            with self._connect() as connection:

                connection.execute(
                    """
                    INSERT INTO translation_jobs (
                        id,
                        input_file,
                        source_language,
                        target_language,
                        priority,
                        status,
                        progress,
                        preprocessing,
                        retry_count,
                        output_file,
                        error_message,
                        created_at,
                        started_at,
                        completed_at,
                        cancelled_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        input_file = excluded.input_file,
                        source_language = excluded.source_language,
                        target_language = excluded.target_language,
                        priority = excluded.priority,
                        status = excluded.status,
                        progress = excluded.progress,
                        preprocessing = excluded.preprocessing,
                        retry_count = excluded.retry_count,
                        output_file = excluded.output_file,
                        error_message = excluded.error_message,
                        created_at = excluded.created_at,
                        started_at = excluded.started_at,
                        completed_at = excluded.completed_at,
                        cancelled_at = excluded.cancelled_at,
                        updated_at = excluded.updated_at
                    """,
                    (
                        data["id"],
                        data["input_file"],
                        data["source_language"],
                        data["target_language"],
                        data["priority"],
                        data["status"],
                        json.dumps(
                            data["progress"]
                        ),
                        json.dumps(
                            data["preprocessing"]
                        ),
                        data["retry_count"],
                        data["output_file"],
                        data["error_message"],
                        data["created_at"],
                        data["started_at"],
                        data["completed_at"],
                        data["cancelled_at"],
                        data["updated_at"],
                    ),
                )

                connection.commit()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to persist job | job_id=%s",
                job.id,
            )

            raise RuntimeError(
                "Unable to persist translation job."
            ) from exc

        logger.debug(
            "Job persisted | job_id=%s | status=%s",
            job.id,
            job.status.value,
        )

    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retrieve a job by ID.
        """

        try:

            with self._connect() as connection:

                row = connection.execute(
                    """
                    SELECT *
                    FROM translation_jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                ).fetchone()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to retrieve job | job_id=%s",
                job_id,
            )

            raise RuntimeError(
                "Unable to retrieve translation job."
            ) from exc

        if row is None:

            logger.debug(
                "Job not found | job_id=%s",
                job_id,
            )

            return None

        return self._build_job(row)

    def delete(
        self,
        job_id: str,
    ) -> None:
        """
        Delete a job.
        """

        try:

            with self._connect() as connection:

                connection.execute(
                    """
                    DELETE FROM translation_jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                )

                connection.commit()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to delete job | job_id=%s",
                job_id,
            )

            raise RuntimeError(
                "Unable to delete translation job."
            ) from exc

        logger.info(
            "Job deleted | job_id=%s",
            job_id,
        )

    def exists(
        self,
        job_id: str,
    ) -> bool:
        """
        Return True if a job exists.
        """

        try:

            with self._connect() as connection:

                row = connection.execute(
                    """
                    SELECT 1
                    FROM translation_jobs
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (job_id,),
                ).fetchone()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to check job existence | job_id=%s",
                job_id,
            )

            raise RuntimeError(
                "Unable to check job existence."
            ) from exc

        return row is not None

    def list_all(
        self,
    ) -> list[TranslationJob]:
        """
        Return all stored jobs.
        """

        try:

            with self._connect() as connection:

                rows = connection.execute(
                    """
                    SELECT *
                    FROM translation_jobs
                    ORDER BY created_at
                    """
                ).fetchall()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to list translation jobs."
            )

            raise RuntimeError(
                "Unable to list translation jobs."
            ) from exc

        jobs = [
            self._build_job(row)
            for row in rows
        ]

        logger.debug(
            "Jobs loaded | count=%s",
            len(jobs),
        )

        return jobs

    def find_active_job(
        self,
        input_file: Path,
    ) -> TranslationJob | None:
        """
        Return an active job for the given input file.
        """

        active_statuses = (
            JobStatus.PENDING.value,
            JobStatus.QUEUED.value,
            JobStatus.RUNNING.value,
            JobStatus.RETRYING.value,
        )

        try:

            with self._connect() as connection:

                row = connection.execute(
                    """
                    SELECT *
                    FROM translation_jobs
                    WHERE input_file = ?
                      AND status IN (?, ?, ?, ?)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (
                        str(input_file),
                        *active_statuses,
                    ),
                ).fetchone()

        except sqlite3.Error as exc:

            logger.exception(
                "Failed to find active job | input=%s",
                input_file,
            )

            raise RuntimeError(
                "Unable to find active translation job."
            ) from exc

        if row is None:

            return None

        return self._build_job(row)

    # =========================================================================
    # Reconstruction
    # =========================================================================

    @staticmethod
    def _build_job(
        row: sqlite3.Row,
    ) -> TranslationJob:
        """
        Reconstruct TranslationJob from a SQLite row.
        """

        progress_data = json.loads(
            row["progress"]
        )

        preprocessing_data = json.loads(
            row["preprocessing"]
        )

        preprocessing = PreprocessingState(
            audio_extracted=preprocessing_data.get(
                "audio_extracted",
                False,
            ),
            audio_file=(
                Path(
                    preprocessing_data["audio_file"]
                )
                if preprocessing_data.get(
                    "audio_file"
                )
                else None
            ),
            asr_completed=preprocessing_data.get(
                "asr_completed",
                False,
            ),
            transcript_file=(
                Path(
                    preprocessing_data[
                        "transcript_file"
                    ]
                )
                if preprocessing_data.get(
                    "transcript_file"
                )
                else None
            ),
        )

        job = TranslationJob(
            input_file=Path(
                row["input_file"]
            ),
            source_language=row[
                "source_language"
            ],
            target_language=row[
                "target_language"
            ],
            id=row["id"],
            priority=JobPriority(
                row["priority"]
            ),
            status=JobStatus(
                row["status"]
            ),
            progress=JobProgress(
                stage=progress_data["stage"],
                percentage=progress_data[
                    "percentage"
                ],
                message=progress_data.get(
                    "message",
                    "",
                ),
            ),
            preprocessing=preprocessing,
            retry_count=row["retry_count"],
            output_file=(
                Path(row["output_file"])
                if row["output_file"]
                else None
            ),
            error_message=row[
                "error_message"
            ],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            started_at=(
                datetime.fromisoformat(
                    row["started_at"]
                )
                if row["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromisoformat(
                    row["completed_at"]
                )
                if row["completed_at"]
                else None
            ),
            cancelled_at=(
                datetime.fromisoformat(
                    row["cancelled_at"]
                )
                if row["cancelled_at"]
                else None
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
        )

        # Rehydration must not create a new domain event.
        job.clear_events()

        return job