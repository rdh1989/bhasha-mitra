from .application_exception import ApplicationException


class ValidationError(ApplicationException):
    """
    Raised when an incoming request
    fails application validation.
    """

    pass