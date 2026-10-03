#!/usr/bin/env python3
"""Convert restored, hash-pinned owner-mirror GeoTIFF inputs into aligned working arrays.

This command never contacts DrivenData. First restore the public owner mirrors from the checked-in manifest,
then run this preparation step. Inputs and generated caches are kept outside Git.

    python scripts/restore_h31_data.py --group all
    python scripts/prepare_data.py
    python scripts/build_features.py
    python scripts/build_addons.py
    python scripts/build_h31_features.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.prepare import prepare_inputs  # noqa: E402


def main() -> None:
    d, w = data_dir(), work_dir()
    if not (d / "sample_submission.tif").is_file() or not (d / "training_features.tif").is_file():
        raise SystemExit("missing restored owner-mirror inputs; run scripts/restore_h31_data.py --group all first")
    w.mkdir(parents=True, exist_ok=True)
    start = time.time()
    stats = prepare_inputs(d, w)
    print(f"Prepared aligned arrays: {stats}")
    print(f"Work directory: {w}")
    print(f"Elapsed: {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
