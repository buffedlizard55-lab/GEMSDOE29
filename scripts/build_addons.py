#!/usr/bin/env python3
"""Build the add-on static columns (H26-1 cross-scarp contrast, H26-2 DEM line orientation)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.features import build_addons  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402


def main() -> None:
    d, w = data_dir(), work_dir()
    t0 = time.time()
    foot = np.load(w / "bands" / "_footprint.npy")
    names = build_addons(w / "bands", foot, d / "external", w / "addons.npy")
    print(f"built add-on columns {names} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
