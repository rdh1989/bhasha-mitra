"""
Exception raised when an uploaded file has an unsupported extension.
"""

from __future__ import annotations

from collections.abc import Iterable

from .application_exception import ApplicationException


class InvalidFileExtensionError(ApplicationException):
    """
    Raised when an uploaded file has an unsupported extension.
    """

    status_code = 400
    error_code = "INVALID_FILE_EXTENSION"

    def __init__(
        self,
        extension: str,
        allowed_extensions: Iterable[str] | None = None,
    ) -> None:
        details = {
            "extension": extension,
        }

        if allowed_extensions is not None:
            details["allowed_extensions"] = sorted(allowed_extensions)

        super().__init__(
            message=f"File extension '{extension}' is not supported.",
            details=details,
        )