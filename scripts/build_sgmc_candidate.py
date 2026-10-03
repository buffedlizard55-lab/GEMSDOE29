#!/usr/bin/env python3
"""Build the SGMC external-inventory candidate GeoTIFF (alternative hypothesis file).

Emission: dots covering the state-geologic-map (SGMC) fault inventory, restricted to pixels that are
neither supplied-catalogue pixels nor within 300 m of one, at the same dot budget as the group's best
historical file (44,090). Both proxy scores for this file are written into the receipt; it is **not**
slot-recommended under the repository's registered gate (it loses the catalogue-hidden gate), it is an
external-data hypothesis offered for owner review only.

    GEMS_DATA_DIR=/tmp/gemsdoe29-data python3 scripts/build_sgmc_candidate.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.coverage import greedy_coverage  # noqa: E402
from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.submission import check_file, content_id, make_filename, make_note, sha256_file, write_submission, zip_single  # noqa: E402

DATE = "20261003"
BUDGET = 44_090
MIN_SEP = 2.8


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "docs" / "downloads"))
    args = ap.parse_args()

    data = data_dir()
    with rasterio.open(data / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(data / "labels.tif") as ds:
        labels = ds.read(1) > 0
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) > 0
    off = sgmc & ~labels & ~binary_dilation(labels, iterations=3)
    prior = gaussian_filter(off.astype(np.float32), 1.2)
    result = greedy_coverage(prior, foot, budgets=(BUDGET,), radius_px=3.0, min_sep_px=MIN_SEP, gain_floor=0.0)
    emission = result.emissions[BUDGET]
    print(f"SGMC inventory: total {int(sgmc.sum()):,} px; off-catalogue {int(off.sum()):,} px; "
          f"dots {int(emission.sum()):,}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cid = content_id(emission.astype(np.float32), foot, labels)
    tif = out_dir / make_filename(f"sgmc-off-catalogue-{BUDGET // 1000}k", DATE, cid, "nan")
    write_submission(emission.astype(np.float32), data / "sample_submission.tif", tif, outside="nan")
    checks = check_file(tif, data / "sample_submission.tif")
    receipt = dict(
        file=tif.name,
        content_id=cid,
        sha256=sha256_file(tif),
        bytes=tif.stat().st_size,
        hypothesis="predict the state-geologic-map (NBMG/SGMC) fault inventory where it is not the supplied catalogue",
        external_data="external/derived_sgmc_faults_100m_u8.tif (owner-mirrored SGMC-derived layer; free official state-map data)",
        emitted_pixels=int(emission.sum()),
        min_sep_px=MIN_SEP,
        scoreboard="evidence/candidate_scoreboard.json",
        status=(
            "format-validated; NOT slot-recommended under the registered gate (loses the catalogue-hidden proxy); "
            "unscored; offered for owner review as an external-inventory alternative"
        ),
        note=make_note("GEMSDOE29 SGMC", "state-map fault inventory off-catalogue; unscored; review only", cid),
        format_check=checks,
    )
    (out_dir / f"checks-{tif.stem}.json").write_text(json.dumps(receipt, indent=2, default=float) + "\n")
    zip_single(tif)
    print(f"wrote {tif.name} ({tif.stat().st_size:,} B) + checks + zip; format ok: {checks.get('ok_to_upload')}")
    return 0 if checks.get("ok_to_upload") else 1


if __name__ == "__main__":
    raise SystemExit(main())
