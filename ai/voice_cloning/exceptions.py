"""Voice-cloning specific exceptions."""


class VoiceCloningError(RuntimeError):
    """Base exception for voice-cloning failures."""


class VoiceCloningConfigurationError(VoiceCloningError):
    """Raised when the voice-cloning model/configuration is invalid."""


class VoiceCloningDependencyError(VoiceCloningError):
    """Raised when optional voice-cloning dependencies are unavailable."""
