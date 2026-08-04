from .validation_error import ValidationError


class InvalidLanguagePairError(ValidationError):
    """
    Raised when source and target
    languages form an invalid pair.
    """

    pass