"""Tests for the CLI adapter."""

from __future__ import annotations

import json
from pathlib import Path

from file_organizer.cli import main


def test_cli_organizes(populated_dir: Path, capsys) -> None:
    code = main([str(populated_dir), "--workers", "1"])
    assert code == 0
    assert (populated_dir / "images" / "photo.jpg").exists()


def test_cli_dry_run_json(populated_dir: Path, capsys) -> None:
    code = main([str(populated_dir), "--dry-run", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["moved"] == 5
    assert (populated_dir / "photo.jpg").exists()  # untouched


def test_cli_missing_source_returns_error(tmp_path: Path) -> None:
    assert main([str(tmp_path / "ghost")]) == 1


def test_cli_rejects_zero_workers(populated_dir: Path) -> None:
    import pytest

    with pytest.raises(SystemExit):
        main([str(populated_dir), "--workers", "0"])
