"""
Logging handlers for Bhasha Mitra.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from infrastructure.logging.constants import (
    APPLICATION_LOG,
    BACKUP_COUNT,
    ERROR_LOG,
    JOB_LOG,
    LOG_DIRECTORY,
    MAX_FILE_SIZE,
)
from infrastructure.logging.exceptions import LogDirectoryError
from infrastructure.logging.filters import (
    ApplicationFilter,
    ErrorFilter,
    JobFilter,
)
from infrastructure.logging.formatter import (
    ConsoleFormatter,
    ErrorFormatter,
    FileFormatter,
    JobFormatter,
)


class HandlerFactory:
    """
    Factory responsible for creating logging handlers.
    """

    @staticmethod
    def ensure_log_directory() -> None:
        """
        Create log directory if it does not exist.
        """
        try:
            Path(LOG_DIRECTORY).mkdir(
                parents=True,
                exist_ok=True,
            )
        except Exception as ex:
            raise LogDirectoryError(str(LOG_DIRECTORY)) from ex

    @staticmethod
    def create_console_handler(
        level: int,
    ) -> logging.Handler:

        handler = logging.StreamHandler()

        handler.setLevel(level)

        handler.setFormatter(ConsoleFormatter())

        return handler

    @staticmethod
    def create_application_handler(
        level: int,
    ) -> logging.Handler:

        HandlerFactory.ensure_log_directory()

        handler = RotatingFileHandler(
            filename=LOG_DIRECTORY / APPLICATION_LOG,
            maxBytes=MAX_FILE_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )

        handler.setLevel(level)

        handler.setFormatter(FileFormatter())

        handler.addFilter(ApplicationFilter())

        return handler

    @staticmethod
    def create_error_handler() -> logging.Handler:

        HandlerFactory.ensure_log_directory()

        handler = RotatingFileHandler(
            filename=LOG_DIRECTORY / ERROR_LOG,
            maxBytes=MAX_FILE_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )

        handler.setLevel(logging.ERROR)

        handler.setFormatter(ErrorFormatter())

        handler.addFilter(ErrorFilter())

        return handler

    @staticmethod
    def create_job_handler(
        level: int,
    ) -> logging.Handler:

        HandlerFactory.ensure_log_directory()

        handler = RotatingFileHandler(
            filename=LOG_DIRECTORY / JOB_LOG,
            maxBytes=MAX_FILE_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )

        handler.setLevel(level)

        handler.setFormatter(JobFormatter())

        handler.addFilter(JobFilter())

        return handler