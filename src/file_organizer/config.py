"""Configuration model and loading logic.

The organizer is driven by a mapping of *category name* -> *list of file
extensions*. A sensible default is baked in so the tool works with zero config,
but users can override it with a JSON file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping

from .errors import ConfigError

# Default category -> extensions mapping. Extensions are stored *without* the
# leading dot and in lowercase for cheap, case-insensitive matching.
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff"],
    "documents": ["pdf", "doc", "docx", "txt", "md", "rtf", "odt"],
    "spreadsheets": ["xls", "xlsx", "csv", "ods"],
    "archives": ["zip", "tar", "gz", "bz2", "7z", "rar", "xz"],
    "audio": ["mp3", "wav", "flac", "aac", "ogg", "m4a"],
    "video": ["mp4", "mkv", "mov", "avi", "webm", "flv"],
    "code": ["py", "js", "ts", "java", "c", "cpp", "go", "rs", "rb", "sh"],
}

# Folder used for anything that does not match a known category.
DEFAULT_FALLBACK_CATEGORY = "other"


@dataclass(frozen=True)
class Config:
    """Immutable, validated organizer configuration.

    Attributes:
        categories: Mapping of category name -> set-like list of extensions.
        fallback_category: Folder name for unmatched files.
    """

    categories: Mapping[str, List[str]] = field(
        default_factory=lambda: dict(DEFAULT_CATEGORIES)
    )
    fallback_category: str = DEFAULT_FALLBACK_CATEGORY

    def __post_init__(self) -> None:
        # Build a fast reverse index: extension -> category. Done once, up front.
        index: Dict[str, str] = {}
        for category, extensions in self.categories.items():
            if not isinstance(category, str) or not category.strip():
                raise ConfigError(f"Invalid category name: {category!r}")
            for ext in extensions:
                norm = ext.lower().lstrip(".")
                if norm in index and index[norm] != category:
                    raise ConfigError(
                        f"Extension '.{norm}' mapped to multiple categories: "
                        f"'{index[norm]}' and '{category}'"
                    )
                index[norm] = category
        # frozen dataclass: assign via object.__setattr__.
        object.__setattr__(self, "_extension_index", index)

    def category_for_extension(self, extension: str) -> str:
        """Return the category folder for a file extension (no leading dot)."""
        index: Dict[str, str] = object.__getattribute__(self, "_extension_index")
        return index.get(extension.lower().lstrip("."), self.fallback_category)


def load_config(path: Path | None) -> Config:
    """Load a :class:`Config` from a JSON file, or return the default config.

    The JSON schema is::

        {
          "categories": {"images": ["jpg", "png"], ...},
          "fallback_category": "other"
        }

    Args:
        path: Path to a JSON config file, or ``None`` for defaults.

    Raises:
        ConfigError: If the file cannot be read or is structurally invalid.
    """
    if path is None:
        return Config()

    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read config file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a JSON object.")

    categories = raw.get("categories", DEFAULT_CATEGORIES)
    if not isinstance(categories, dict):
        raise ConfigError("'categories' must be an object of name -> [extensions].")

    normalized: Dict[str, List[str]] = {}
    for name, exts in categories.items():
        if not isinstance(exts, list) or not all(isinstance(e, str) for e in exts):
            raise ConfigError(f"Category '{name}' must map to a list of strings.")
        normalized[name] = [e.lower().lstrip(".") for e in exts]

    fallback = raw.get("fallback_category", DEFAULT_FALLBACK_CATEGORY)
    if not isinstance(fallback, str) or not fallback.strip():
        raise ConfigError("'fallback_category' must be a non-empty string.")

    return Config(categories=normalized, fallback_category=fallback)
