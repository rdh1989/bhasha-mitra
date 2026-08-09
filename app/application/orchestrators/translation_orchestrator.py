"""
===============================================================================
BHASHA MITRA
Translation Orchestrator
===============================================================================

Module:
    translation_orchestrator.py

Layer:
    Application

Description:
    Application orchestrator for the complete translation workflow.

Responsibilities:
    - Create translation job
    - Queue translation job
    - Start translation job
    - Execute translation workflow
    - Update job progress
    - Complete translation job
    - Fail translation job
    - Cancel translation job
    - Retry translation job

Master workflow:

    Pre-check
        ↓
    Translation
        ↓
    Subtitle
        ↓
    Dubbing
        ↓
    Export
        ↓
    Complete Job

The individual stage implementations are supplied to the orchestrator.
The orchestrator owns the execution order only.

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from domain.entities import TranslationJob

from app.application.dto.create_job_request import (
    CreateJobRequest,
)
from app.application.services.job_service import (
    JobService,
)


class TranslationOrchestrator:
    """
    Orchestrates the complete translation workflow.
    """

    def __init__(
        self,
        job_service: JobService,
        translation_step: Callable[[TranslationJob], None] | None = None,
        subtitle_step: Callable[[TranslationJob], None] | None = None,
        dubbing_step: Callable[[TranslationJob], None] | None = None,
        export_step: Callable[[TranslationJob], Path] | None = None,
    ) -> None:

        self._job_service = job_service

        self._translation_step = translation_step
        self._subtitle_step = subtitle_step
        self._dubbing_step = dubbing_step
        self._export_step = export_step

    # =========================================================================
    # Job lifecycle
    # =========================================================================

    def create_job(
        self,
        request: CreateJobRequest,
    ) -> TranslationJob:
        """
        Create a new translation job.
        """

        return self._job_service.create(
            request
        )

    def queue_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Queue a translation job.
        """

        return self._job_service.queue(
            job_id
        )

    def start_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Mark a translation job as started.
        """

        return self._job_service.start(
            job_id
        )

    # =========================================================================
    # Master translation workflow
    # =========================================================================

    def execute(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Execute the complete translation workflow.

        Workflow:

            Translation
                ↓
            Subtitle
                ↓
            Dubbing
                ↓
            Export
                ↓
            Complete
        """

        job = self._job_service.get(
            job_id
        )

        if job is None:
            return None

        try:

            # =================================================================
            # Start
            # =================================================================

            job = self.start_job(
                job_id
            )

            if job is None:
                return None

            # =================================================================
            # Translation
            # =================================================================

            self.update_progress(
                job_id=job_id,
                stage="translation",
                percentage=0,
                message="Translation started.",
            )

            self._run_translation(
                job
            )

            self.update_progress(
                job_id=job_id,
                stage="translation",
                percentage=100,
                message="Translation completed.",
            )

            # =================================================================
            # Subtitle
            # =================================================================

            self.update_progress(
                job_id=job_id,
                stage="subtitle",
                percentage=0,
                message="Subtitle generation started.",
            )

            self._run_subtitle(
                job
            )

            self.update_progress(
                job_id=job_id,
                stage="subtitle",
                percentage=100,
                message="Subtitle generation completed.",
            )

            # =================================================================
            # Dubbing
            # =================================================================

            self.update_progress(
                job_id=job_id,
                stage="dubbing",
                percentage=0,
                message="Dubbing started.",
            )

            self._run_dubbing(
                job
            )

            self.update_progress(
                job_id=job_id,
                stage="dubbing",
                percentage=100,
                message="Dubbing completed.",
            )

            # =================================================================
            # Export
            # =================================================================

            self.update_progress(
                job_id=job_id,
                stage="export",
                percentage=0,
                message="Video export started.",
            )

            output_file = self._run_export(
                job
            )

            self.update_progress(
                job_id=job_id,
                stage="export",
                percentage=100,
                message="Video export completed.",
            )

            # =================================================================
            # Complete
            # =================================================================

            return self.complete_job(
                job_id=job_id,
                output_file=output_file,
            )

        except Exception as exc:

            self.fail_job(
                job_id=job_id,
                error_message=str(exc),
            )

            raise

    # =========================================================================
    # Workflow stages
    # =========================================================================

    def _run_translation(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute translation stage.
        """

        if self._translation_step is None:

            raise RuntimeError(
                "Translation step is not configured."
            )

        self._translation_step(
            job
        )

    def _run_subtitle(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute subtitle stage.
        """

        if self._subtitle_step is None:

            raise RuntimeError(
                "Subtitle step is not configured."
            )

        self._subtitle_step(
            job
        )

    def _run_dubbing(
        self,
        job: TranslationJob,
    ) -> None:
        """
        Execute dubbing stage.
        """

        if self._dubbing_step is None:

            raise RuntimeError(
                "Dubbing step is not configured."
            )

        self._dubbing_step(
            job
        )

    def _run_export(
        self,
        job: TranslationJob,
    ) -> Path:
        """
        Execute export stage.
        """

        if self._export_step is None:

            raise RuntimeError(
                "Export step is not configured."
            )

        output_file = self._export_step(
            job
        )

        if not output_file:

            raise RuntimeError(
                "Export did not return an output file."
            )

        return output_file

    # =========================================================================
    # Job state
    # =========================================================================

    def update_progress(
        self,
        job_id: str,
        stage: str,
        percentage: int,
        message: str = "",
    ) -> TranslationJob | None:
        """
        Update translation progress.
        """

        return self._job_service.update_progress(
            job_id=job_id,
            stage=stage,
            percentage=percentage,
            message=message,
        )

    def complete_job(
        self,
        job_id: str,
        output_file: Path,
    ) -> TranslationJob | None:
        """
        Mark translation as completed.
        """

        return self._job_service.complete(
            job_id,
            output_file,
        )

    def fail_job(
        self,
        job_id: str,
        error_message: str,
    ) -> TranslationJob | None:
        """
        Mark translation as failed.
        """

        return self._job_service.fail(
            job_id,
            error_message,
        )

    def cancel_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Cancel a translation job.
        """

        return self._job_service.cancel(
            job_id
        )

    def retry_job(
        self,
        job_id: str,
    ) -> TranslationJob | None:
        """
        Retry a failed translation job.
        """

        return self._job_service.retry(
            job_id
        )