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
