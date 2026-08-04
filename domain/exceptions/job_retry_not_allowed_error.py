"""
===============================================================================
Module: Job Retry Not Allowed Error
===============================================================================
"""

from domain.exceptions.domain_exception import DomainException


class JobRetryNotAllowedError(DomainException):
    """
    Raised when retry is not permitted.
    """

    default_message = "Job cannot be retried."