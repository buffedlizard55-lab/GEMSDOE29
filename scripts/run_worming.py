#!/usr/bin/env python3
"""Compute corrected worming rasters and audits (label-free).

Usage: python scripts/run_worming.py
The registered six-level persistence is bounded to [0,1]; amplitude retention is a separate
[0,2] raster. No competition endpoint is accessed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems29 import gridio, paths, worming  # noqa: E402


def main() -> int:
    WORK = paths.DATA / "work" / "worming"
    WORK.mkdir(parents=True, exist_ok=True)
    raw = paths.DATA / "bridge" / "training_features.tif"
    import rasterio as rio
    with rio.open(paths.DATA / "bridge" / "sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    rtp, v1 = gridio.read_band(raw, 2)
    grav, v2 = gridio.read_band(raw, 13)
    tmi, v3 = gridio.read_band(raw, 14)
    if not (v1 == v2).all() or not (v1 == v3).all():
        raise SystemExit("band footprints disagree inside training_features.tif")
    # IR-29-FOOTPRINT-DIFF: template and feature-stack masks differ slightly. Worming is calculated
    # on the feature-stack mask; all submission outputs and scores use the template mask.
    calc = v1
    print(f"footprint diff: template={valid.sum():,} features={calc.sum():,} "
          f"in-template-not-features={(valid & ~calc).sum():,} in-features-not-template={(calc & ~valid).sum():,}")

    mag = worming.run_field("mag", rtp, calc, out_dir=WORK)
    grav_out = worming.run_field("grav", grav, calc, out_dir=WORK)
    Pm, Pg = mag["P"], grav_out["P"]
    Sm, Sg = mag["Sr"], grav_out["Sr"]
    Em, Eg = mag["E0"] > 0, grav_out["E0"] > 0
    jointP = np.where(Em & Eg, np.minimum(Pm, Pg), np.where(Em, Pm, Pg)).astype(np.float32)
    jointS = np.where(Em & Eg, np.minimum(Sm, Sg), np.where(Em, Sm, Sg)).astype(np.float32)
    joint_valid = (Em | Eg) & calc
    gridio.write_raster(jointP, WORK / "worm_joint_persist.tif", valid=joint_valid, dtype="float32")
    gridio.write_raster(jointS, WORK / "worm_joint_strength_ratio.tif", valid=joint_valid, dtype="float32")
    gridio.write_raster(joint_valid.astype(np.float32), WORK / "worm_joint_defined.tif",
                        valid=valid, dtype="float32")
    for name, arr in (("mag persistence", Pm), ("gravity persistence", Pg),
                      ("joint persistence", jointP)):
        if not np.isfinite(arr[calc]).all() or np.any((arr[calc] < 0) | (arr[calc] > 1)):
            raise SystemExit(f"{name} violates the required finite [0,1] range")
    if not np.isfinite(jointS[calc]).all() or np.any((jointS[calc] < 0) | (jointS[calc] > 2)):
        raise SystemExit("joint amplitude retention violates the finite [0,2] range")

    audit = worming.line_audit(mag, calc)
    # UC operator cross-check against the owner-mirrored contractor TMI_up150 grid (u8 ranks, band 4).
    with rio.open(paths.DATA / "external" / "geodawn_extensions_u8.tif") as ds:
        up150 = ds.read(4)
    xchk = worming.uc_crosscheck(tmi, up150, v3)

    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "historical_correction": "Current implementation follows the preregistered nearest-valid FFT padding and bounded persistence. Earlier median-overwritten padding and n_levels-2 normalization defects invalidated superseded H29 screens and WORMRANK artifacts; snapshots and hashes are under evidence/history/. See knowledge/05_pre_run_implementation_audit_2026-10-03.md and knowledge/06_post_screen_review_2026-10-03.md.",
        "provenance": {
            "feature_stack_sha256": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
            "sample_template_sha256": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
            "source_status": "pinned owner mirrors, not organizer-authenticated",
        },
        "magnetic": mag["receipt"], "gravity": grav_out["receipt"],
        "line_audit_magnetic": audit, "uc_crosscheck": xchk,
        "footprint_diff": {"template": int(valid.sum()), "features": int(calc.sum()),
                            "in_template_not_features": int((valid & ~calc).sum()),
                            "in_features_not_template": int((calc & ~valid).sum())},
        "joint": {"n_joint_persistent_deep": int(((jointP >= worming.TAU_PERSIST) & joint_valid).sum()),
                  "n_level0_edges_union": int(joint_valid.sum()),
                  "max_persistence": float(jointP[joint_valid].max()) if joint_valid.any() else 0.0,
                  "max_strength_ratio": float(jointS[joint_valid].max()) if joint_valid.any() else 0.0},
        "constants": {"LADDER_M": list(worming.LADDER_M), "EDGE_QUANTILE": worming.EDGE_QUANTILE,
                      "TOL_PX": worming.TOL_PX, "TOL_SLOPE_PX_PER_100M": worming.TOL_SLOPE_PX_PER_100M,
                      "TAU_PERSIST": worming.TAU_PERSIST,
                      "persistence_bounds": [0.0, 1.0],
                      "strength_ratio_bounds": [0.0, 2.0],
                      "persistence_definition": "last_matched_level_index / (number_of_levels - 1)"},
        "rasters": ["worm_mag_persist.tif", "worm_grav_persist.tif", "worm_joint_persist.tif",
                    "worm_joint_defined.tif", "worm_mag_hlast_m.tif", "worm_grav_hlast_m.tif",
                    "worm_mag_strength_ratio.tif", "worm_grav_strength_ratio.tif",
                    "worm_joint_strength_ratio.tif", "worm_mag_edge0.tif", "worm_grav_edge0.tif",
                    "worm_mag_strike.tif", "worm_grav_strike.tif"],
    }
    paths.EVIDENCE.mkdir(exist_ok=True)
    (paths.EVIDENCE / "worming_receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
