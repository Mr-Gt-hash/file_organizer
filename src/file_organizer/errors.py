"""Custom exception hierarchy for the file_organizer package.

A dedicated hierarchy lets callers (and the CLI) distinguish *expected* domain
failures (bad config, missing directory) from genuinely unexpected bugs.
"""

from __future__ import annotations


class FileOrganizerError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(FileOrganizerError):
    """Raised when a configuration file is missing, malformed, or invalid."""


class SourceDirectoryError(FileOrganizerError):
    """Raised when the source directory is missing or not a directory."""


class MoveError(FileOrganizerError):
    """Raised when an individual file operation fails irrecoverably."""
