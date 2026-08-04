"""
===============================================================================
Module: Invalid Job Progress Error
===============================================================================
"""

from domain.exceptions.domain_exception import DomainException


class InvalidJobProgressError(DomainException):
    """
    Raised when invalid progress values are supplied.
    """

    default_message = "Invalid job progress."