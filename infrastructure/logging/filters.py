"""
Custom logging filters for Bhasha Mitra.
"""

from __future__ import annotations

import logging


class ErrorFilter(logging.Filter):
    """
    Allow only ERROR and CRITICAL log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return record.levelno >= logging.ERROR


class ApplicationFilter(logging.Filter):
    """
    Allow log records below ERROR level.

    Prevents duplicate entries between
    application.log and error.log.
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return record.levelno < logging.ERROR


class JobFilter(logging.Filter):
    """
    Allow only translation job logs.

    Usage:

        logger.info(
            "Translation started",
            extra={"job_log": True}
        )
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return getattr(record, "job_log", False)


class PerformanceFilter(logging.Filter):
    """
    Reserved for future performance logging.

    Usage:

        logger.info(
            "Inference completed",
            extra={"performance_log": True}
        )
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return getattr(record, "performance_log", False)


class AuditFilter(logging.Filter):
    """
    Reserved for future audit logging.

    Usage:

        logger.info(
            "User changed provider",
            extra={"audit_log": True}
        )
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return getattr(record, "audit_log", False)