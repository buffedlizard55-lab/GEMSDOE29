#!/usr/bin/env python3
"""Independently verify every shipped download in docs/downloads against the artifact ledger.

Re-reads each .tif/.zip from disk with fresh file handles, re-checks the official format contract
(single-band float32, EPSG:32611, 3730x3292, 100 m, [0,1] finite in the template footprint, NaN or
zeros outside per its suffix, exact transform match, pixel counts, ZIP contents) and recomputes
SHA-256. Exits non-zero on any failure. This is the site's guarantee that a one-click download can
never fail the DrivenData validator for a FORMAT reason.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gems29.submission import sha256_file, verify_files  # noqa: E402


def main() -> int:
    dl = ROOT / "docs" / "downloads"
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    ledger = json.loads((ROOT / "registry" / "artifact_ledger.json").read_text())
    n_fail = 0
    for key, art in ledger["artifacts"].items():
        stem = art.get("stem")
        if not stem:
            continue
        checks = verify_files(dl, stem, foot_mask=foot, expected_px=art.get("px"))
        n_fail += sum(1 for c in checks.values() if not c["pass"])
        print(f"{key}: {len(checks)} checks, fails={sum(1 for c in checks.values() if not c['pass'])}")
        (dl / f"checks-{stem}.json").write_text(json.dumps({"stem": stem, "checks": checks}, indent=2))
    print("verify_downloads:", "ALL PASS" if n_fail == 0 else f"{n_fail} FAILURES")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
