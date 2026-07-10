"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def populated_dir(tmp_path: Path) -> Path:
    """Create a directory with a mix of file types for organizing."""
    files = ["photo.jpg", "report.pdf", "song.mp3", "script.py", "mystery.xyz"]
    for name in files:
        (tmp_path / name).write_text("content", encoding="utf-8")
    return tmp_path
