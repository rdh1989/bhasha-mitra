"""
===============================================================================
Module: Job Cancel Not Allowed Error
===============================================================================
"""

from domain.exceptions.domain_exception import DomainException


class JobCancelNotAllowedError(DomainException):
    """
    Raised when a job cannot be cancelled.
    """

    default_message = "Job cannot be cancelled."