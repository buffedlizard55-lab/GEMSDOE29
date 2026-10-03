"""Path resolution. Large inputs live outside Git (``GEMS_DATA_DIR``, default ``<repo>/data``)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Directory holding restored competition inputs (never committed)."""
    return Path(os.environ.get("GEMS_DATA_DIR", ROOT / "data")).expanduser()


def work_dir() -> Path:
    """Scratch directory for regenerable caches (never committed)."""
    return Path(os.environ.get("GEMS_WORK_DIR", data_dir() / "work")).expanduser()
