from .validation_error import ValidationError


class UnsupportedLanguageError(ValidationError):
    """
    Raised when a language
    is not supported.
    """

    pass