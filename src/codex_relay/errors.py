class RelayError(Exception):
    """Base user-facing error."""


class ProfileNotFoundError(RelayError):
    """Requested profile does not exist."""


class InvalidProfileError(RelayError):
    """Profile files or metadata are invalid."""


class SwitchError(RelayError):
    """Activating a profile failed."""
