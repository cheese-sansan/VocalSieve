"""Stable exception hierarchy exposed by the public SDK."""


class VocalSieveError(Exception):
    """Base class for expected application failures."""


class ConfigurationError(VocalSieveError, ValueError):
    """The supplied job configuration is invalid."""


class JobNotFoundError(VocalSieveError, KeyError):
    """A requested job does not exist."""


class JobStateError(VocalSieveError, RuntimeError):
    """The requested operation is invalid for the current job state."""


class BackendUnavailableError(VocalSieveError, RuntimeError):
    """A required audio or inference backend is not usable."""
