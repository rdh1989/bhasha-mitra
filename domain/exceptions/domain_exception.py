"""
===============================================================================
Module: Domain Exception
Project: Bhasha Mitra
Layer: Domain
===============================================================================

Base exception for all domain-related errors.
"""

from __future__ import annotations


class DomainException(Exception):
    """
    Base class for all domain exceptions.
    """

    default_message = "A domain error has occurred."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)