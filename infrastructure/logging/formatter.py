"""
Custom log formatter for Bhasha Mitra.
"""

from __future__ import annotations

import logging

from infrastructure.logging.constants import (
    DATE_FORMAT,
    DEFAULT_FORMAT,
)


class LogFormatter(logging.Formatter):
    """
    Standard formatter used across the application.
    """

    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DATE_FORMAT,
    ) -> None:

        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
        )


class ConsoleFormatter(LogFormatter):
    """
    Formatter for console logging.

    Reserved for future enhancements such as:
        - Colored output
        - Rich logging
        - Emoji/status indicators
    """

    pass


class FileFormatter(LogFormatter):
    """
    Formatter for application log files.
    """

    pass


class ErrorFormatter(LogFormatter):
    """
    Formatter dedicated to error.log.

    Can later be extended to include stack traces,
    request IDs, correlation IDs, etc.
    """

    pass


class JobFormatter(LogFormatter):
    """
    Formatter dedicated to job.log.

    Future versions may include:
        - Job ID
        - Provider
        - Processing time
        - Translation language
    """

    pass