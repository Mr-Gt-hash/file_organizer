# file-organizer

A small, production-ready command-line tool that organizes the files in a
directory into category folders (images, documents, audio, …) based on their
extension. Built with clean architecture, full type hints, structured logging,
robust error handling, and a complete unit-test suite.

## Features

- **Zero-config** — sensible built-in categories; override with a JSON file.
- **Dry-run mode** — preview every move before touching disk (`--dry-run`).
- **Recursive** — organize nested directories (`--recursive`).
- **Concurrent** — thread pool for fast, I/O-bound moves (`--workers N`).
- **Collision-safe** — never overwrites; appends `_1`, `_2`, … instead.
- **Idempotent** — re-running skips files already in category folders.
- **Structured logging** — `-v` for debug, `-q` for quiet, JSON summary option.
- **Standard library only** — no runtime dependencies.

## Installation

    python -m pip install -e .            # installs the `file-organizer` command
    python -m pip install -e ".[dev]"     # + pytest/mypy for development

Run without installing:

    PYTHONPATH=src python -m file_organizer --help

## Usage

    file-organizer /path/to/messy/folder                 # organize in place
    file-organizer ~/Downloads --dry-run                 # preview only
    file-organizer ~/Downloads --recursive --workers 8   # nested + concurrent
    file-organizer ~/Downloads -c examples/config.example.json
    file-organizer ~/Downloads --json                    # machine-readable summary

Exit codes: `0` success · `1` fatal error · `2` some files failed to move.

## Example

Given `downloads/` with photo.jpg, report.pdf, song.mp3, script.py, mystery.xyz:

    $ file-organizer downloads/
    Moved 5 file(s); skipped 0, failed 0.

Produces images/photo.jpg, documents/report.pdf, audio/song.mp3,
code/script.py, other/mystery.xyz.

## Development

    python -m pip install -e ".[dev]"
    pytest
    mypy src

## License

MIT
