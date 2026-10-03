"""Frozen competition grid constants, all verified against data/bridge/sample_submission.tif."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
WORK = DATA / "work"
EVIDENCE = ROOT / "evidence"

GRID = {
    "width": 3292,
    "height": 3730,
    "crs": "EPSG:32611",
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
    "pixel_m": 100.0,
    "footprint_px": 5_167_373,
    "bounds_utm11n": [243350.0, 4135550.0, 572550.0, 4508550.0],
}

# The official metric's spatial support is a 300 m triangular kernel at 100 m pixels.
RADIUS_PX = 3.0

# Two restore layouts are in use: ``scripts/restore_data.py`` writes the core manifest to
# ``data/bridge/`` and ``scripts/restore_h31_data.py`` writes the H31 group manifest to ``data/``. The
# template is the same hash-pinned file in both, so resolvers must accept either (IR-29-CHECK-TEMPLATE-ROOT).
def resolve(relative: str, *, base: Path | None = None) -> Path:
    """Return the first existing candidate for ``relative`` under the data dir; ``bridge/`` is preferred.

    ``relative`` is a bare file name such as ``sample_submission.tif`` or ``training_features.tif``. When
    nothing exists on disk the legacy ``bridge/`` path is returned so callers report the manifest location
    rather than a silently wrong one.
    """
    root = DATA if base is None else base
    for cand in (root / "bridge" / relative, root / relative):
        if cand.is_file():
            return cand
    return root / "bridge" / relative


def template_path(*, base: Path | None = None) -> Path:
    """The submission template, whichever restore layout is present."""
    root = DATA if base is None else base
    return resolve("sample_submission.tif", base=root)
