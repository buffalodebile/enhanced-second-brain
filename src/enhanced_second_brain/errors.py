class ESBError(RuntimeError):
    """Base user-facing toolkit error."""


class ConfigurationError(ESBError):
    """Configuration could not be resolved or is unsafe."""


class ValidationError(ESBError):
    """Knowledge content failed validation."""


class SafetyError(ESBError):
    """A requested operation violated a safety invariant."""
