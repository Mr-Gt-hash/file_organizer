"""Core organizing logic.

Design notes
------------
* The planning phase (:meth:`Organizer.plan`) is *pure*: it only reads the
  filesystem and returns a list of intended moves. This makes ``--dry-run``
  trivial and the logic easy to unit-test without touching disk state.
* The execution phase (:meth:`Organizer.execute`) performs the moves, with
  collision-safe renaming and optional concurrency for I/O-bound throughput.
"""

from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List

from .config import Config
from .errors import MoveError, SourceDirectoryError
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PlannedMove:
    """A single intended move from ``source`` to ``destination``."""

    source: Path
    destination: Path
    category: str


@dataclass
class OrganizeResult:
    """Summary of an organize run."""

    planned: int = 0
    moved: int = 0
    skipped: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "planned": self.planned,
            "moved": self.moved,
            "skipped": self.skipped,
            "failed": self.failed,
        }


class Organizer:
    """Plans and executes the organization of a source directory."""

    def __init__(self, config: Config) -> None:
        self._config = config

    # ----------------------------------------------------------------- plan
    def _iter_files(self, source: Path, recursive: bool) -> Iterator[Path]:
        """Yield candidate files under ``source``.

        Uses ``os.scandir`` (via ``Path.iterdir``/``rglob``) lazily so we never
        materialize a huge list in memory for large directories.
        """
        if recursive:
            for path in source.rglob("*"):
                if path.is_file():
                    yield path
        else:
            for path in source.iterdir():
                if path.is_file():
                    yield path

    def plan(self, source: Path, recursive: bool = False) -> List[PlannedMove]:
        """Compute the list of moves without touching the filesystem state.

        Args:
            source: Directory to organize.
            recursive: Whether to descend into subdirectories.

        Raises:
            SourceDirectoryError: If ``source`` is not an existing directory.
        """
        if not source.exists():
            raise SourceDirectoryError(f"Source directory does not exist: {source}")
        if not source.is_dir():
            raise SourceDirectoryError(f"Source path is not a directory: {source}")

        # Category folders we will create; skip files already inside them so
        # re-running the tool is idempotent.
        category_names = set(self._config.categories) | {self._config.fallback_category}

        planned: List[PlannedMove] = []
        for path in self._iter_files(source, recursive):
            # Don't re-organize files that already live in a category folder.
            if any(part in category_names for part in path.relative_to(source).parts[:-1]):
                logger.debug("Skipping already-organized file: %s", path)
                continue

            extension = path.suffix.lstrip(".")
            category = self._config.category_for_extension(extension)
            destination = source / category / path.name
            planned.append(PlannedMove(path, destination, category))

        logger.info("Planned %d move(s) from %s", len(planned), source)
        return planned

    # -------------------------------------------------------------- execute
    @staticmethod
    def _resolve_collision(destination: Path) -> Path:
        """Return a non-colliding destination path.

        If ``destination`` exists, append ``_1``, ``_2``, ... before the suffix.
        """
        if not destination.exists():
            return destination
        stem, suffix, parent = destination.stem, destination.suffix, destination.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _do_move(self, move: PlannedMove, dry_run: bool) -> bool:
        """Execute a single move. Returns True if moved, False if skipped."""
        if move.source == move.destination:
            return False

        if dry_run:
            logger.info("[dry-run] %s -> %s", move.source, move.destination)
            return True

        try:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            final = self._resolve_collision(move.destination)
            shutil.move(str(move.source), str(final))
            logger.debug("Moved %s -> %s", move.source, final)
            return True
        except OSError as exc:
            raise MoveError(f"Failed to move {move.source} -> {move.destination}: {exc}") from exc

    def execute(
        self,
        moves: Iterable[PlannedMove],
        dry_run: bool = False,
        workers: int = 1,
    ) -> OrganizeResult:
        """Execute planned moves, optionally concurrently.

        Args:
            moves: The planned moves to perform.
            dry_run: If True, log intended actions without touching disk.
            workers: Number of threads for concurrent I/O (>=1). File moves are
                I/O-bound, so threads give real speedups without the GIL cost of
                CPU work.
        """
        moves = list(moves)
        result = OrganizeResult(planned=len(moves))

        if workers <= 1 or dry_run:
            for move in moves:
                self._run_one(move, dry_run, result)
            return result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._do_move, m, dry_run): m for m in moves}
            for future in as_completed(futures):
                move = futures[future]
                try:
                    moved = future.result()
                    result.moved += int(moved)
                    result.skipped += int(not moved)
                except MoveError as exc:
                    result.failed += 1
                    logger.error("%s", exc)
        return result

    def _run_one(self, move: PlannedMove, dry_run: bool, result: OrganizeResult) -> None:
        """Sequential single-move helper that updates ``result`` in place."""
        try:
            moved = self._do_move(move, dry_run)
            result.moved += int(moved)
            result.skipped += int(not moved)
        except MoveError as exc:
            result.failed += 1
            logger.error("%s", exc)
