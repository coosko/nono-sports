"""Common project exceptions."""


class NonoSportsError(Exception):
    """Base exception for project-specific errors."""


class ConfigurationError(NonoSportsError):
    """Raised when the project configuration is invalid."""


class AuthenticationError(NonoSportsError):
    """Raised when an external authentication flow fails."""
