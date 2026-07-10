"""Tests for the core organizer."""

from __future__ import annotations

from pathlib import Path

import pytest

from file_organizer.config import Config
from file_organizer.errors import SourceDirectoryError
from file_organizer.organizer import Organizer, PlannedMove


def test_plan_assigns_correct_categories(populated_dir: Path) -> None:
    org = Organizer(Config())
    plan = org.plan(populated_dir)
    by_name = {m.source.name: m.category for m in plan}
    assert by_name == {
        "photo.jpg": "images",
        "report.pdf": "documents",
        "song.mp3": "audio",
        "script.py": "code",
        "mystery.xyz": "other",
    }


def test_plan_is_pure_does_not_move(populated_dir: Path) -> None:
    org = Organizer(Config())
    org.plan(populated_dir)
    # Files still in place after planning.
    assert (populated_dir / "photo.jpg").exists()


def test_plan_missing_source_raises(tmp_path: Path) -> None:
    org = Organizer(Config())
    with pytest.raises(SourceDirectoryError):
        org.plan(tmp_path / "ghost")


def test_execute_moves_files(populated_dir: Path) -> None:
    org = Organizer(Config())
    result = org.execute(org.plan(populated_dir), workers=1)
    assert result.moved == 5
    assert (populated_dir / "images" / "photo.jpg").exists()
    assert (populated_dir / "other" / "mystery.xyz").exists()
    assert not (populated_dir / "photo.jpg").exists()


def test_dry_run_moves_nothing(populated_dir: Path) -> None:
    org = Organizer(Config())
    result = org.execute(org.plan(populated_dir), dry_run=True)
    assert result.moved == 5  # counts intended moves
    assert (populated_dir / "photo.jpg").exists()  # but disk unchanged
    assert not (populated_dir / "images").exists()


def test_idempotent_rerun(populated_dir: Path) -> None:
    org = Organizer(Config())
    org.execute(org.plan(populated_dir))
    # Second run should find nothing to do (files already in category folders).
    second = org.plan(populated_dir)
    assert second == []


def test_collision_gets_unique_name(populated_dir: Path) -> None:
    org = Organizer(Config())
    (populated_dir / "images").mkdir()
    (populated_dir / "images" / "photo.jpg").write_text("existing", encoding="utf-8")
    org.execute([m for m in org.plan(populated_dir) if m.source.name == "photo.jpg"])
    assert (populated_dir / "images" / "photo.jpg").exists()
    assert (populated_dir / "images" / "photo_1.jpg").exists()


def test_concurrent_execute(populated_dir: Path) -> None:
    org = Organizer(Config())
    result = org.execute(org.plan(populated_dir), workers=4)
    assert result.moved == 5


def test_recursive_plan(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.png").write_text("x", encoding="utf-8")
    org = Organizer(Config())
    plan = org.plan(tmp_path, recursive=True)
    assert any(m.source.name == "deep.png" for m in plan)
