"""
===============================================================================
Module: Invalid Job State Error
===============================================================================
"""

from domain.exceptions.domain_exception import DomainException


class InvalidJobStateError(DomainException):
    """
    Raised when an invalid job state transition is attempted.
    """

    default_message = "Invalid job state transition."