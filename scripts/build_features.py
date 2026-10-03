#!/usr/bin/env python3
"""Build the static (A-D) feature memmap in the work directory (never committed)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.features import build_static  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.prepare import prepare_inputs  # noqa: E402


def main() -> None:
    d, w = data_dir(), work_dir()
    w.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if not (w / "bands" / "_footprint.npy").exists():
        print("prepare:", prepare_inputs(d, w))
    foot = np.load(w / "bands" / "_footprint.npy")
    out = w / "static_ABCD.npy"
    names = build_static(w / "bands", foot, d / "external", out, "ABCD")
    print(f"built {len(names)} static features in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
