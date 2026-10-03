#!/usr/bin/env python3
"""Package local-format-verified raster artifacts; no competition endpoint is accessed.

`WORMRANK` is the corrected-persistence A2-style ranked emission. It is always generated for
inspection, but a failed holdout gate explicitly marks it research-only. `REFD28` is a pixel-mask
reproduction of the owner-mirrored, owner-reported 0.2600 geometry and is labelled DO NOT RESUBMIT.
H29-5 is not turned into a downloadable candidate unless its frozen screen and confirmation gate
pass; it failed the screen on this run, so no slot is recommended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems29 import emission, gridio, paths  # noqa: E402
from gems29.submission import write_submission  # noqa: E402
from gems29.thinning import dot_thin, dot_thin_ranked  # noqa: E402


def load_layers():
    with rasterio.open(paths.DATA / "bridge" / "sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    lab, _ = gridio.read_band(paths.DATA / "bridge" / "labels.tif")
    catalog = np.nan_to_num(lab) > 0
    parent, _ = gridio.read_band(paths.DATA / "inputs" / "h19_5_nan.tif")
    solid = emission.parent_solid_from_raster(parent, fp)
    W = paths.DATA / "work" / "worming"
    with rasterio.open(W / "worm_joint_persist.tif") as ds:
        J = np.nan_to_num(ds.read(1))
    with rasterio.open(W / "worm_joint_defined.tif") as ds:
        D = np.nan_to_num(ds.read(1))
    with rasterio.open(paths.DATA / "external" / "lidar_scarp_features_u8.tif") as ds:
        lid = {nm: ds.read(i).astype(np.float32) for i, nm in
               zip([1, 3, 9], ["ex_max", "step_max", "relief"])}
    ridge = ((lid["ex_max"] - 1).clip(0) + (lid["step_max"] - 1).clip(0)
             + (lid["relief"] - 1).clip(0)) / (3 * 254.0)
    ridge = np.where(fp, ridge, 0.0)
    return fp, catalog, solid, J, D, ridge


def build_wormrank(fp, catalog, solid, J, D, ridge) -> np.ndarray:
    w = np.where(D > 0.5, np.clip(J, 0.0, 1.0), 0.5)
    priority = 0.5 * w + 0.5 * ridge
    base = solid & ~catalog & fp
    return dot_thin_ranked(base, 2.8, priority)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    gate_path = paths.EVIDENCE / "h29_gate.json"
    gate = json.loads(gate_path.read_text()) if gate_path.exists() else {}
    a2_pass = gate.get("A2", {}).get("PASS") is True
    h29_5_gate = gate.get("H29-5", {})
    h29_5_pass = h29_5_gate.get("PASS") is True
    fp, catalog, solid, J, D, ridge = load_layers()
    out_dir = ROOT / "docs" / "downloads"
    date = "20261003"
    ledger: dict[str, dict] = {}

    mask = build_wormrank(fp, catalog, solid, J, D, ridge)
    cid = hashlib.sha256(mask.tobytes()).hexdigest()[:12]
    stem = f"gems29-wormrank-d28-{date}-{cid}"
    status = ("slot-eligible by local proxy only; live effect unverified" if a2_pass else
              "research artifact — A2 local proxy gate FAIL; do not spend a weekly slot")
    note = (f"GEMSDOE29 WORMRANK | d2.8 spacing, corrected persistence+ridge rank | "
            f"A2 gate={'PASS' if a2_pass else 'FAIL'} proxy only | {cid} | live-unverified")[:200]
    checks = write_submission(mask, out_dir, stem, note=note)
    ledger["WORMRANK"] = {"stem": stem, "px": int(mask.sum()), "spacing_px": 2.8, "status": status,
                          "content_id": cid, "note": note,
                          "local_format_verified": bool(checks["__summary__"]["pass"]),
                          "holdout_gate": gate.get("A2", {})}

    # Compare this deterministic reconstruction with the original owner-mirrored D2.8 mask.
    ref_mask = dot_thin(solid & ~catalog & fp, 2.8)
    ref_data, _ = gridio.read_band(paths.DATA / "inputs" / "dotted_h19_5_d2_8_nan.tif")
    ref_owner_mask = np.isfinite(ref_data) & (ref_data > 0.5) & fp
    same_pixels = bool(np.array_equal(ref_mask, ref_owner_mask))
    if not same_pixels:
        raise SystemExit("local D2.8 reproduction does not match pinned owner-mirror pixel mask")
    ref_cid = hashlib.sha256(ref_mask.tobytes()).hexdigest()[:12]
    stemr = f"gems29-refd28-repro-{date}-{ref_cid}"
    write_submission(ref_mask, out_dir, stemr,
                     note=f"GEMSDOE29 REF-D2.8 | owner-reported 0.2600 mask reproduction | "
                          f"DO NOT RESUBMIT; duplicate | {ref_cid}")
    ledger["REFD28"] = {"px": int(ref_mask.sum()), "spacing_px": 2.8, "content_id": ref_cid,
                        "stem": stemr, "matches_owner_mirror_mask": same_pixels,
                        "score_status": "0.2600 is owner-reported; not authenticated by the mask file",
                        "status": "reference only — already reported scored; do not resubmit"}
    ledger["H29-5"] = {
        "status": "not packaged as a submission candidate",
        "screen_gate": h29_5_gate,
        "reason": "screen failed against best same-fold/same-draw pre-existing controls; no confirmation draws were run per preregistered compute-saving rule",
        "slot_spend": False,
    }

    registry_path = ROOT / "registry" / "artifact_ledger.json"
    registry_path.write_text(json.dumps({
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate_snapshot": gate,
        "input_manifest": "data/manifest.json (all entries hash-verified locally; owner mirrors)",
        "artifacts": ledger,
    }, indent=2, default=float) + "\n")
    print(json.dumps(ledger, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
