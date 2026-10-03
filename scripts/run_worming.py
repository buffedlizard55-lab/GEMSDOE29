#!/usr/bin/env python3
"""Compute the worming rasters + audits (label-free). Writes evidence/worming_receipt.json.

Usage:  python scripts/run_worming.py
"""
from __future__ import annotations

import json
import sys
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
    # IR-29-FOOTPRINT-DIFF: the feature stack and the sample-submission template differ slightly
    # (61 template-footprint cells are nodata in the features; 1,540 feature cells lie outside).
    # Worming computes on the FEATURES valid mask; submissions always use the template footprint.
    calc = v1
    diff_in = int((calc & valid).size - 0)  # noqa
    print(f"footprint diff: template={valid.sum():,} features={calc.sum():,} "
          f"in-template-not-features={(valid & ~calc).sum():,} in-features-not-template={(calc & ~valid).sum():,}")

    mag = worming.run_field("mag", rtp, calc, out_dir=WORK)
    grav_out = worming.run_field("grav", grav, calc, out_dir=WORK)
    Pm, Pg = mag["P"], grav_out["P"]
    Em, Eg = mag["E0"] > 0, grav_out["E0"] > 0
    jointP = np.where(Em & Eg, np.minimum(Pm, Pg), np.where(Em, Pm, Pg)).astype(np.float32)
    joint_valid = (Em | Eg) & valid
    gridio.write_raster(jointP, WORK / "worm_joint_persist.tif", valid=joint_valid, dtype="float32")
    gridio.write_raster(joint_valid.astype(np.float32), WORK / "worm_joint_defined.tif",
                        valid=valid, dtype="float32")
    assert np.isfinite(np.where(joint_valid, jointP, 0.0)).all()

    audit = worming.line_audit(mag, calc)
    # UC operator cross-check against the contractor TMI_up150 grid (u8 ranks, band 4)
    import rasterio
    with rasterio.open(paths.DATA / "external" / "geodawn_extensions_u8.tif") as ds:
        up150 = ds.read(4)
    xchk = worming.uc_crosscheck(tmi, up150, v3)

    receipt = {
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                         .isoformat(timespec="seconds"),
        "magnetic": mag["receipt"], "gravity": grav_out["receipt"],
        "line_audit_magnetic": audit, "uc_crosscheck": xchk,
        "footprint_diff": {"template": int(valid.sum()), "features": int(calc.sum()),
                            "in_template_not_features": int((valid & ~calc).sum()),
                            "in_features_not_template": int((calc & ~valid).sum())},
        "joint": {"n_joint_persistent_deep": int(((jointP >= 0.5)).sum()),
                  "n_level0_edges_union": int(joint_valid.sum())},
        "constants": {"LADDER_M": list(worming.LADDER_M), "EDGE_QUANTILE": worming.EDGE_QUANTILE,
                      "TOL_PX": worming.TOL_PX, "TOL_SLOPE": worming.TOL_SLOPE_PX_PER_100M,
                      "TAU_PERSIST": worming.TAU_PERSIST},
        "rasters": ["worm_mag_persist.tif", "worm_grav_persist.tif", "worm_joint_persist.tif",
                    "worm_joint_defined.tif", "worm_mag_hlast_m.tif", "worm_grav_hlast_m.tif",
                    "worm_mag_edge0.tif", "worm_grav_edge0.tif", "worm_mag_strike.tif",
                    "worm_grav_strike.tif"],
    }
    paths.EVIDENCE.mkdir(exist_ok=True)
    (paths.EVIDENCE / "worming_receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
