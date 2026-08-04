"""
Base exception for the Application layer.

All custom application exceptions must inherit from this class.

This class is framework-independent and should not import FastAPI,
Starlette, or any HTTP-related modules.
"""

from __future__ import annotations

from typing import Any


class ApplicationException(Exception):
    """
    Base class for all application exceptions.

    Attributes:
        status_code: HTTP status code returned by the API layer.
        error_code: Stable application-specific error code.
        message: Human-readable error message.
        details: Optional additional error details.
    """

    status_code: int = 400
    error_code: str = "APPLICATION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.details = details

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the exception into a serializable dictionary.

        Returns:
            Dictionary representation of the exception.
        """
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        return self.message