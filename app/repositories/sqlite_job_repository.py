"""
===============================================================================
BHASHA MITRA
SQLite Job Repository
===============================================================================

Module:
    sqlite_job_repository.py

Layer:
    Application Repository

Description:
    SQLite implementation of the JobRepository interface.

Responsibilities:
    - Persist TranslationJob metadata
    - Retrieve jobs by ID
    - Delete jobs
    - Check job existence
    - List all jobs
    - Find active jobs by input file

Database:
    database/bhasha_mitra.db

Important:
    This repository stores job metadata only.
    Video, audio, subtitle, and final-video files remain filesystem artifacts.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository
from domain.entities import TranslationJob
from domain.enums.job_priority import JobPriority
from domain.enums.job_status import JobStatus
from domain.value_objects.job_progress import JobProgress


logger = logging.getLogger(__name__)


class SQLiteJobRepository(JobRepository):
    """
    SQLite implementation of JobRepository.
    """

    def __init__(
        self,
        database_path: Path,
    ) -> None:
        """
        Initialize the SQLite repository.
        """

        self._database_path = database_path

        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    # =========================================================================
    # Database
    # =========================================================================

    def _connect(self) -> sqlite3.Connection:
        """
        Create a SQLite database connection.
        """

        connection = sqlite3.connect(
            self._database_path,
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize_database(self) -> None:
        """
        Create the jobs table and indexes if they do not exist.
        """

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    input_file TEXT NOT NULL,
                    output_file TEXT,
                    retry_count INTEGER NOT NULL,
                    progress TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    cancelled_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status
                ON jobs(status)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_input_file
                ON jobs(input_file)
                """
            )

            connection.commit()

        logger.info(
            "SQLite job repository initialized | database=%s",
            self._database_path,
        )

    # =========================================================================
    # Mapping
    # =========================================================================

    @staticmethod
    def _job_to_row(
        job: TranslationJob,
    ) -> tuple:
        """
        Convert TranslationJob into SQLite column values.
        """

        data = job.to_dict()

        return (
            data["id"],
            data["status"],
            job.priority.value,
            data["source_language"],
            data["target_language"],
            data["input_file"],
            data["output_file"],
            data["retry_count"],
            json.dumps(
                data["progress"],
                ensure_ascii=False,
            ),
            data["error_message"],
            data["created_at"],
            data["started_at"],
            data["completed_at"],
            data["cancelled_at"],
            data["updated_at"],
        )

    @staticmethod
    def _row_to_job(
        row: sqlite3.Row,
    ) -> TranslationJob:
        """
        Reconstruct TranslationJob from a SQLite row.
        """

        progress_data = json.loads(
            row["progress"]
        )

        progress = JobProgress(
            stage=progress_data["stage"],
            percentage=progress_data["percentage"],
            message=progress_data.get(
                "message",
                "",
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
            progress=progress,
            retry_count=row[
                "retry_count"
            ],
            output_file=(
                Path(row["output_file"])
                if row["output_file"]
                else None
            ),
            error_message=row[
                "error_message"
            ],
            created_at=TranslationJob._parse_datetime(
                row["created_at"]
            ),
            started_at=(
                TranslationJob._parse_datetime(
                    row["started_at"]
                )
                if row["started_at"]
                else None
            ),
            completed_at=(
                TranslationJob._parse_datetime(
                    row["completed_at"]
                )
                if row["completed_at"]
                else None
            ),
            cancelled_at=(
                TranslationJob._parse_datetime(
                    row["cancelled_at"]
                )
                if row["cancelled_at"]
                else None
            ),
            updated_at=TranslationJob._parse_datetime(
                row["updated_at"]
            ),
        )

        job.clear_events()

        return job

    # =========================================================================
    # Repository
    # =========================================================================

    def save(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Persist a TranslationJob.

        Existing jobs are updated by their ID.
        """

        values = self._job_to_row(job)

        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO jobs (
                    id,
                    status,
                    priority,
                    source_language,
                    target_language,
                    input_file,
                    output_file,
                    retry_count,
                    progress,
                    error_message,
                    created_at,
                    started_at,
                    completed_at,
                    cancelled_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(id)
                DO UPDATE SET
                    status = excluded.status,
                    priority = excluded.priority,
                    source_language = excluded.source_language,
                    target_language = excluded.target_language,
                    input_file = excluded.input_file,
                    output_file = excluded.output_file,
                    retry_count = excluded.retry_count,
                    progress = excluded.progress,
                    error_message = excluded.error_message,
                    created_at = excluded.created_at,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    cancelled_at = excluded.cancelled_at,
                    updated_at = excluded.updated_at
                """,
                values,
            )

            connection.commit()

        logger.debug(
            "Translation job persisted | "
            "job_id=%s status=%s",
            job.id,
            job.status.value,
        )

    def get(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retrieve a TranslationJob by ID.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        if row is None:

            logger.debug(
                "Translation job not found | job_id=%s",
                job_id,
            )

            return None

        return self._row_to_job(row)

    def delete(
        self,
        job_id: str,
    ) -> None:
        """
        Delete a TranslationJob by ID.
        """

        with self._connect() as connection:

            connection.execute(
                """
                DELETE FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            )

            connection.commit()

        logger.debug(
            "Translation job deleted | job_id=%s",
            job_id,
        )

    def exists(
        self,
        job_id: str,
    ) -> bool:
        """
        Check whether a TranslationJob exists.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT 1
                FROM jobs
                WHERE id = ?
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()

        return row is not None

    def list_all(
        self,
    ) -> list[TranslationJob]:
        """
        Return all persisted TranslationJob instances.
        """

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY created_at ASC
                """
            ).fetchall()

        jobs = [
            self._row_to_job(row)
            for row in rows
        ]

        logger.debug(
            "Translation jobs retrieved | count=%s",
            len(jobs),
        )

        return jobs

    def find_active_job(
        self,
        input_file: Path,
    ) -> TranslationJob | None:
        """
        Find the latest unfinished job for an input file.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE input_file = ?
                  AND status NOT IN (
                      'COMPLETED',
                      'FAILED',
                      'CANCELLED'
                  )
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(input_file),),
            ).fetchone()

        if row is None:
            return None

        job = self._row_to_job(row)

        logger.debug(
            "Active translation job found | "
            "job_id=%s input_file=%s",
            job.id,
            input_file,
        )

        return job