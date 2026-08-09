"""
===============================================================================
BHASHA MITRA
Repository Factory
===============================================================================

Module:
    repository_factory.py

Layer:
    Application / Repository

Description:
    Creates the repository implementations used by the application.

Responsibilities:
    - Provide the active JobRepository implementation
    - Centralize repository construction
    - Keep SQLite database configuration in one place

Author  : Team Bhasha Mitra
Version : 1.0.0
===============================================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.application.interfaces.job_repository import JobRepository
from app.repository.sqlite_job_repository import SQLiteJobRepository


logger = logging.getLogger(__name__)


class RepositoryFactory:
    """
    Creates application repository implementations.
    """

    @staticmethod
    def create_job_repository(
        database_path: Path,
    ) -> JobRepository:
        """
        Create the application's JobRepository.

        SQLite is the active persistence implementation.
        """

        logger.info(
            "Creating SQLite JobRepository | database=%s",
            database_path,
        )

        return SQLiteJobRepository(
            database_path=database_path,
        )