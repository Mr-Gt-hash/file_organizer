"""Command-line interface for file_organizer.

Thin adapter over the library: parse args -> configure logging -> load config
-> plan -> execute -> print summary. All *policy* lives in the library; the CLI
only handles I/O and exit codes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import load_config
from .errors import FileOrganizerError
from .logging_config import configure_logging, get_logger
from .organizer import Organizer

logger = get_logger(__name__)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PARTIAL = 2  # some files failed to move


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser (separated out for testability)."""
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Organize files in a directory into category folders by extension.",
    )
    parser.add_argument("source", type=Path, help="Directory to organize.")
    parser.add_argument(
        "-c", "--config", type=Path, default=None,
        help="Path to a JSON config file (defaults to built-in categories).",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true",
        help="Recurse into subdirectories.",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="Show what would happen without moving any files.",
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=4, metavar="N",
        help="Number of worker threads for concurrent moves (default: 4).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit the run summary as JSON on stdout.",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase log verbosity (-v for DEBUG).",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Only log warnings and errors.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(verbosity=args.verbose, quiet=args.quiet)

    if args.workers < 1:
        parser.error("--workers must be >= 1")

    try:
        config = load_config(args.config)
        organizer = Organizer(config)
        planned = organizer.plan(args.source, recursive=args.recursive)
        result = organizer.execute(
            planned, dry_run=args.dry_run, workers=args.workers
        )
    except FileOrganizerError as exc:
        # Expected, user-facing failure: no traceback, just a clear message.
        logger.error("%s", exc)
        return EXIT_ERROR

    summary = result.as_dict()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        verb = "Would move" if args.dry_run else "Moved"
        print(
            f"{verb} {summary['moved']} file(s); "
            f"skipped {summary['skipped']}, failed {summary['failed']}."
        )

    return EXIT_PARTIAL if result.failed else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
