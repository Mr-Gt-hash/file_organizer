"""Centralized logging configuration.

Keeping logging setup in one place means the library never calls
``basicConfig`` at import time (which would hijack a host application's
logging). The CLI is the only caller that configures handlers.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(verbosity: int = 0, quiet: bool = False) -> None:
    """Configure the root logger for the CLI.

    Args:
        verbosity: 0 -> INFO, 1 -> DEBUG. Higher values still map to DEBUG.
        quiet: When True, only WARNING and above are emitted.
    """
    if quiet:
        level = logging.WARNING
    elif verbosity >= 1:
        level = logging.DEBUG
    else:
        level = logging.INFO

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()  # idempotent: safe to call multiple times (e.g. in tests)
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger. Thin wrapper for a consistent import site."""
    return logging.getLogger(name)
