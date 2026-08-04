"""
Custom exceptions for the logging module.
"""


class LoggingError(Exception):
    """
    Base exception for all logging-related errors.
    """

    pass


class LoggerInitializationError(LoggingError):
    """
    Raised when the logging framework cannot be initialized.
    """

    pass


class InvalidLogLevelError(LoggingError):
    """
    Raised when an invalid log level is configured.
    """

    def __init__(self, level: str):
        super().__init__(f"Invalid log level: '{level}'")


class LogDirectoryError(LoggingError):
    """
    Raised when the log directory cannot be created or accessed.
    """

    def __init__(self, directory: str):
        super().__init__(
            f"Unable to access log directory: '{directory}'"
        )


class LogFileError(LoggingError):
    """
    Raised when a log file cannot be created or opened.
    """

    def __init__(self, filename: str):
        super().__init__(
            f"Unable to open log file: '{filename}'"
        )