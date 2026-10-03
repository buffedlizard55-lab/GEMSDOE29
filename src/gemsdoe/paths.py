"""Path resolution. Large inputs live outside Git (``GEMS_DATA_DIR``, default ``<repo>/data``)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Directory holding restored competition inputs (never committed)."""
    return Path(os.environ.get("GEMS_DATA_DIR", ROOT / "data")).expanduser()


TEMPLATE_CANDIDATES = ("bridge/sample_submission.tif", "sample_submission.tif")


def template_path() -> Path:
    """Resolve the owner-mirror submission template, whichever restore layout is on disk.

    ``scripts/restore_data.py`` (legacy core manifest) writes ``GEMS_DATA_DIR/bridge/sample_submission.tif``;
    ``scripts/restore_h31_data.py`` (H31 group manifest, the restore the current screens and the site's
    reproduce commands use) writes ``GEMS_DATA_DIR/sample_submission.tif``. Preferring an existing file keeps
    one checker working after either restore; with neither present the legacy bridge path is returned because
    that is the location ``data/manifest.json`` names.
    """
    data = data_dir()
    for rel in TEMPLATE_CANDIDATES:
        p = data / rel
        if p.is_file():
            return p
    return data / TEMPLATE_CANDIDATES[0]


def work_dir() -> Path:
    """Scratch directory for regenerable caches (never committed)."""
    return Path(os.environ.get("GEMS_WORK_DIR", data_dir() / "work")).expanduser()
