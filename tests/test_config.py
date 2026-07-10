"""Tests for the config module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from file_organizer.config import Config, load_config
from file_organizer.errors import ConfigError


def test_default_config_maps_known_extension() -> None:
    cfg = Config()
    assert cfg.category_for_extension("jpg") == "images"
    assert cfg.category_for_extension(".PNG") == "images"  # case + dot insensitive


def test_default_config_uses_fallback_for_unknown() -> None:
    cfg = Config()
    assert cfg.category_for_extension("xyz") == "other"


def test_duplicate_extension_across_categories_raises() -> None:
    with pytest.raises(ConfigError):
        Config(categories={"a": ["txt"], "b": ["txt"]})


def test_load_config_none_returns_default() -> None:
    assert load_config(None).category_for_extension("mp3") == "audio"


def test_load_config_from_file(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(
        json.dumps({"categories": {"pics": ["png"]}, "fallback_category": "misc"}),
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.category_for_extension("png") == "pics"
    assert cfg.category_for_extension("zzz") == "misc"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_load_config_bad_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_bad_shape_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"categories": {"x": "notalist"}}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
