"""
Logger factory for Bhasha Mitra.
"""

from __future__ import annotations

import logging
import threading

from infrastructure.configuration.configuration_manager import ConfigurationManager
from infrastructure.logging.constants import LOGGER_NAME, LOG_LEVELS
from infrastructure.logging.exceptions import (
    InvalidLogLevelError,
    LoggerInitializationError,
)
from infrastructure.logging.handlers import HandlerFactory


class LoggerFactory:
    """
    Thread-safe singleton factory for application loggers.
    """

    _configured = False
    _lock = threading.Lock()

    @classmethod
    def _configure(cls) -> None:
        """
        Configure the root logger once.
        """

        if cls._configured:
            return

        with cls._lock:

            if cls._configured:
                return

            try:

                configuration = ConfigurationManager()

                logging_config = configuration.logging

                level_name = logging_config.get(
                    "level",
                    "INFO",
                ).upper()

                if level_name not in LOG_LEVELS:
                    raise InvalidLogLevelError(level_name)

                level = LOG_LEVELS[level_name]

                root_logger = logging.getLogger(LOGGER_NAME)

                root_logger.setLevel(level)

                root_logger.propagate = False

                if root_logger.handlers:
                    root_logger.handlers.clear()

                root_logger.addHandler(
                    HandlerFactory.create_console_handler(level)
                )

                root_logger.addHandler(
                    HandlerFactory.create_application_handler(level)
                )

                root_logger.addHandler(
                    HandlerFactory.create_error_handler()
                )

                root_logger.addHandler(
                    HandlerFactory.create_job_handler(level)
                )

                cls._configured = True

            except Exception as ex:

                raise LoggerInitializationError(
                    "Failed to initialize logging."
                ) from ex

    @classmethod
    def get_logger(
        cls,
        name: str,
    ) -> logging.Logger:
        """
        Returns a child logger.

        Example:
            logger = LoggerFactory.get_logger(__name__)
        """

        cls._configure()

        return logging.getLogger(f"{LOGGER_NAME}.{name}")