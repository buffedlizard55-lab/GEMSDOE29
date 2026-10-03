#!/usr/bin/env python3
"""Package the H29 candidate emission(s) as format-verified submission GeoTIFFs.

Usage:
  python scripts/build_candidate.py            # builds per gate outcomes in evidence/h29_gate.json
  python scripts/build_candidate.py --force A2 # build a specific arm's full-map file (research label)

Arms offered:
  WORMRANK (A2 geometry, full map): dot_thin_ranked(solid & ~catalogue, 2.8, prio) — the live-proven
    d2.8 spacing with worm/ridge-persistence-informed claiming order. This is a NEW emission
    (different bytes than the 0.2600 mirror) with unchanged geometry, per IR-29-PARENT-OFF-EDGES.
  REF-D28 (reference): a byte-for-byte reproduction of the 44,090-px d2.8 emission that the owner
    reports scored 0.2600 — shipped for format comparison and rollback, flagged DO-NOT-RESUBMIT.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems29 import gridio, emission, paths  # noqa: E402
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
    # ridge composite in the same (q-1)/254 quantised scale the screen's features use
    ridge = ((lid["ex_max"] - 1).clip(0) + (lid["step_max"] - 1).clip(0) + (lid["relief"] - 1).clip(0)) / (3 * 254.0)
    ridge = np.where(fp, ridge, 0.0)
    return fp, catalog, solid, J, D, ridge


def build_wormrank(fp, catalog, solid, J, D, ridge) -> np.ndarray:
    w = np.where(D > 0.5, np.clip(J, 0.0, 1.0), 0.5)
    prio = 0.5 * w + 0.5 * ridge
    base = solid & ~catalog & fp
    return dot_thin_ranked(base, 2.8, prio)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", default=None, help="arm id to build regardless of gate (WORMRANK|REFD28)")
    args = ap.parse_args()
    gate_p = paths.EVIDENCE / "h29_gate.json"
    gate = json.loads(gate_p.read_text()) if gate_p.exists() else {}
    a2 = gate.get("A2", {})
    passed = bool(a2.get("PASS")) if args.force is None else False
    fp, catalog, solid, J, D, ridge = load_layers()
    out_dir = ROOT / "docs" / "downloads"
    date = "20261003"
    ledger = {}

    # --- WORMRANK (A2) full-map ---
    mask = build_wormrank(fp, catalog, solid, J, D, ridge)
    cid = __import__("hashlib").sha256(mask.tobytes()).hexdigest()[:12]
    stem = f"gems29-wormrank-d28-{date}-{cid}"
    status = "SLOT-CANDIDATE (local gate passed; live effect unverified)" if passed else \
             "research artifact — frozen gate NOT passed; do not spend a weekly slot on this unless the owner accepts the risk"
    note = (f"GEMSDOE29 WORMRANK | d2.8 spacing, worm-persistence+ridge ranked order | "
            f"gate={'PASS' if passed else 'FAIL'} proxy ΔDTI see repo | {cid} | live-unverified")[:200]
    write_submission(mask, out_dir, stem, note=note)
    ledger["WORMRANK"] = {"stem": stem, "px": int(mask.sum()), "status": status,
                          "content_id": cid, "note": note}

    # --- REF D2.8 mirror (reproduction of the 0.2600 bytes) ---
    ref_mask = dot_thin(solid & ~catalog & fp, 2.8)
    ref_cid = __import__("hashlib").sha256(ref_mask.tobytes()).hexdigest()[:12]
    ledger["REFD28"] = {"px": int(ref_mask.sum()), "content_id": ref_cid,
                        "matches_sibling_44090": int(ref_mask.sum()) == 44_090}
    stemr = f"gems29-refd28-repro-{date}-{ref_cid}"
    if args.force in (None, "REFD28"):
        write_submission(ref_mask, out_dir, stemr,
                         note=f"GEMSDOE29 REF-D2.8 | reproduction of live-scored 0.2600 geometry | "
                              f"DO NOT RESUBMIT (already scored) | {ref_cid}")
        ledger["REFD28"]["stem"] = stemr

    (ROOT / "registry" / "artifact_ledger.json").parent.mkdir(exist_ok=True)
    (ROOT / "registry" / "artifact_ledger.json").write_text(json.dumps(
        {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "gate_snapshot": gate, "artifacts": ledger}, indent=2, default=float))
    print(json.dumps(ledger, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
