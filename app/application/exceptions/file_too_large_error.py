"""
Exception raised when an uploaded file exceeds the maximum allowed size.
"""

from __future__ import annotations

from .application_exception import ApplicationException


class FileTooLargeError(ApplicationException):
    """
    Raised when the uploaded file exceeds the configured size limit.
    """

    status_code = 400
    error_code = "FILE_TOO_LARGE"

    def __init__(
        self,
        max_size_mb: int,
    ) -> None:
        super().__init__(
            message=f"Maximum allowed file size is {max_size_mb} MB.",
            details={
                "max_size_mb": max_size_mb,
            },
        )