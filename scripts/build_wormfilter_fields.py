#!/usr/bin/env python3
"""Build and cache the H38/H52 worming filter fields (label-free; no fit, no holdout read).

Writes ``data/work/wormfilter_fields.npy`` (``(len(WF_NAMES), n_footprint)`` float32),
``data/work/wormfilter_az_defined.npy`` (the azimuth-defined indicator on the same vector) and
``data/work/wormfilter_fields.json`` (the frozen parameters plus diagnostics, including the per-level
ridge counts and the persistence distribution). Nothing here reads ``labels.tif`` or the catalogue:
the fields are a pure function of the two potential-field bands and the footprint.

    python scripts/build_wormfilter_fields.py [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import work_dir  # noqa: E402
from gemsdoe.wormfilter import WF_NAMES, WormFilterConfig, build_worm_fields  # noqa: E402
from gemsdoe.worms import WormConfig  # noqa: E402

FIELDS = "wormfilter_fields.npy"
AZDEF = "wormfilter_az_defined.npy"
META = "wormfilter_fields.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild even if a cache exists")
    args = parser.parse_args()

    work = work_dir()
    out_fields, out_az, out_meta = work / FIELDS, work / AZDEF, work / META
    if out_fields.is_file() and out_az.is_file() and out_meta.is_file() and not args.force:
        print(f"cached: {out_fields.relative_to(ROOT)} (use --force to rebuild)")
        return 0

    foot = np.load(work / "bands" / "_footprint.npy")
    fi = np.flatnonzero(foot.ravel())
    ladder = WormConfig()
    config = WormFilterConfig()
    t0 = time.time()
    vectors, grids, diag = build_worm_fields(work / "bands", foot, fi, ladder=ladder, config=config)
    elapsed = time.time() - t0

    np.save(out_fields, vectors)
    np.save(out_az, grids["WF_AZ_DEFINED"].ravel()[fi].astype(np.float32))
    diag_out = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        elapsed_s=round(elapsed, 1),
        names=list(WF_NAMES),
        ladder=dict(cell_size_m=float(ladder.cell_size_m), heights_m=list(ladder.heights_m),
                    edge_percentile=float(ladder.edge_percentile), taper_px=int(ladder.taper_px),
                    pad_px=int(ladder.pad_px), boundary_guard_px=int(ladder.boundary_guard_px)),
        config=dict(tol_px=float(config.tol_px), smooth_sigma_px=float(config.smooth_sigma_px),
                    rho_retention=float(config.rho_retention), tau_survival=float(config.tau_survival),
                    tau_azimuth=float(config.tau_azimuth), coherence_min=float(config.coherence_min),
                    convergence_radius_px=float(config.convergence_radius_px),
                    azimuth_sigma_px=float(config.azimuth_sigma_px),
                    min_contrast_fraction=float(config.min_contrast_fraction)),
        level_detector=diag["level_detector"], survival_rule=diag["survival_rule"],
        n_footprint=int(fi.size),
        diagnostics=diag,
        inputs=dict(magnetic_band="02_rtp.npy", gravity_band="13_iso_grav_anom.npy",
                    magnetic_sha256=sha256_file(work / "bands" / "02_rtp.npy"),
                    gravity_sha256=sha256_file(work / "bands" / "13_iso_grav_anom.npy")),
        label_free=True,
    )
    out_meta.write_text(json.dumps(diag_out, indent=2, sort_keys=True) + "\n")

    print(f"built {len(WF_NAMES)} worm-filter fields over {fi.size:,} footprint px in {elapsed:.1f}s")
    for name in WF_NAMES:
        row = vectors[WF_NAMES.index(name)]
        print(f"  {name:16s} nonzero {np.mean(row > 0):.4f}  mean {row.mean():.4f}  max {row.max():.4f}")
    print(f"  WF_AZ_DEFINED    nonzero {np.mean(grids['WF_AZ_DEFINED'].ravel()[fi] > 0):.4f}")
    print(f"wrote {out_fields.relative_to(ROOT)}, {out_az.relative_to(ROOT)}, {out_meta.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
