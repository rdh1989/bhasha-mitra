"""
Exception raised when a requested file cannot be found.
"""

from __future__ import annotations

from .application_exception import ApplicationException


class InputFileNotFoundError(ApplicationException):
    """
    Raised when the requested file does not exist.
    """

    status_code = 404
    error_code = "FILE_NOT_FOUND"

    def __init__(
        self,
        file_name: str,
    ) -> None:
        super().__init__(
            message=f"File '{file_name}' was not found."
        )