#!/usr/bin/env python3
"""H29 holdout screen: worm-gated/ranked emission + worm/thermal head features vs matched controls.

Frozen gate (knowledge/01): PASS iff mean paired quadrant ΔDTI >= +0.005 and >= 3/4 quadrants
positive in both screen draws (0,1), replicated in >= 1 confirmation draw (2,3). Writes
evidence/h29_holdout.json and evidence/h29_gate.json. Compute-saving deviation (documented):
arms far below +0.002 across both screen draws do not receive confirmation fits.

Usage: python scripts/run_holdout_screen.py [--quick]   (--quick = fold 0, draws 0-1 only)
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

from gems29 import emission, features, gridio, head, holdout, paths  # noqa: E402
from gems29.metric import dti_binary  # noqa: E402
from scipy.ndimage import binary_dilation  # noqa: E402


def load_inputs():
    with rasterio.open(paths.DATA / "bridge" / "sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    lab, _ = gridio.read_band(paths.DATA / "bridge" / "labels.tif")
    catalog = np.nan_to_num(lab) > 0
    parent, _ = gridio.read_band(paths.DATA / "inputs" / "h19_5_nan.tif")
    parent = emission.parent_solid_from_raster(parent, valid)
    return valid, catalog, parent


def load_feature_stack(valid):
    feats, _names = features.build_feature_dict(
        raw_path=paths.DATA / "bridge" / "training_features.tif",
        lidar_path=paths.DATA / "external" / "lidar_scarp_features_u8.tif",
        worm_dir=paths.DATA / "work" / "worming",
        known_catalog=np.zeros(valid.shape, bool), valid=valid)
    return feats


def arm_feature_sets(feats: dict) -> dict[str, list[str]]:
    worm_keys = [k for k in ("worm_mag_persist", "worm_grav_persist", "worm_joint_persist",
                             "worm_joint_defined") if k in feats]
    thermal_keys = [k for k in ("probe_dist_norm", "probe_dab", "probe_t2m_close") if k in feats]
    base = [k for k in feats if k.startswith(("raw_", "lid_", "dist_known"))]
    return {"B0": base, "B1": base + worm_keys, "B2": base + thermal_keys}


def add_thermal(feats: dict, valid: np.ndarray):
    zdir = paths.DATA / "gdr" / "probe" / "2m_temperature_probe_INGENIOUS_regional_data"
    shp = zdir / "2m_temperature_probe_n83geo" / "2m_temperature_probe_n83geo.shp"
    if not shp.exists():
        print("thermal probes missing; B2 == B0 by construction")
        return
    from gems29 import thermal
    pr = thermal.load_probes(shp)
    ras = thermal.rasterise(pr, valid)
    feats["probe_dist_norm"] = np.clip(ras["probe_dist_px"], 0, 30).astype(np.float32) / 30.0
    d = np.nan_to_num(ras["dab_nearest"])
    feats["probe_dab"] = np.clip(d / 10.0, -1, 1).astype(np.float32)
    feats["probe_t2m_close"] = np.nan_to_num(ras["t2m_nearest_if_close"]) / 40.0
    print(f"thermal probes: {pr['n_usable']}/{pr['n_records']} usable records")


def dti_fold(emit, hidden, valid, quadrant, known):
    return dti_binary(emit.astype(np.float32), hidden,
                      valid=valid & quadrant, known=known & quadrant)


def score_arm_paired(res, base_res):
    return res["dti"] - base_res["dti"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    valid, catalog, parent = load_inputs()
    folds = holdout.make_quadrant_folds(valid)
    feats = load_feature_stack(valid)
    add_thermal(feats, valid)
    armsets = arm_feature_sets(feats)
    worm_dir = paths.DATA / "work" / "worming"
    with rasterio.open(worm_dir / "worm_joint_persist.tif") as ds:
        jointP = np.nan_to_num(ds.read(1))
    with rasterio.open(worm_dir / "worm_joint_defined.tif") as ds:
        jointDef = np.nan_to_num(ds.read(1))
    joint = {"P": jointP, "defined": jointDef}
    lidar = {k: feats[k] for k in feats if k.startswith("lid_")}

    draws = [0, 1] if args.quick else [0, 1, 2, 3]
    fold_ids = [0] if args.quick else [0, 1, 2, 3]
    results = []
    for draw in draws:
        for fid in fold_ids:
            sp = holdout.make_split(catalog, folds, fid, draw)
            known = catalog & ~sp.hidden
            dist = __import__("scipy.ndimage", fromlist=["distance_transform_edt"]) \
                .distance_transform_edt(~known) - 1.0
            d = np.clip(dist, 0, 30)
            feats["dist_known_px_norm"] = (d / 30.0).astype(np.float32)
            feats["dist_known_collapse"] = np.exp(-d / 4.0).astype(np.float32)
            quadrant = sp.fold_mask
            # ---- A arms (no head) ----
            A = {}
            for arm in ("A0", "A1", "A2"):
                A[arm] = emission.emit_A(parent, valid, quadrant, known, joint, lidar, arm)
            # ---- training rows ----
            collar = binary_dilation(quadrant, iterations=15)
            train_zone = valid & ~collar
            rng = np.random.default_rng(9173 + 31 * fid + draw)
            posf, negf = head.subsample_rows(train_zone.ravel(),
                                             (catalog & train_zone).ravel().astype(np.int8),
                                             rng, neg_ratio=6, max_pos=350_000)
            rowset = np.concatenate([posf, negf])
            ytr = np.concatenate([np.ones(posf.size, np.int8), np.zeros(negf.size, np.int8)])
            q_idx = np.nonzero((quadrant & valid).ravel())[0]
            row = {"draw": draw, "fold": fid, "name": sp.name,
                   "n_hidden": int((sp.hidden & quadrant).sum()),
                   "n_pos_rows": int(posf.size), "n_neg_rows": int(negf.size)}
            base = {}
            A0 = A["A0"]
            emit_info = {}
            for arm in ("A0", "A1", "A2"):
                res = dti_fold(A[arm], sp.hidden & quadrant, valid, quadrant, known)
                emit_info[arm] = {k: res[k] for k in ("dti", "TPw", "FPw", "n_emitted")}
            a0res = dti_fold(A0, sp.hidden & quadrant, valid, quadrant, known)
            for arm in ("A1", "A2"):
                emit_info[arm]["paired_delta"] = emit_info[arm]["dti"] - a0res["dti"]
            row["A"] = emit_info
            # ---- B arms ----
            binfo = {}
            budget = int(A0.sum())
            for arm in ("B0", "B1", "B2"):
                names = armsets[arm]
                Xtr = np.stack([feats[nm].reshape(-1)[rowset] for nm in names], axis=1).astype(np.float32)
                clf = head.fit_head(Xtr, ytr, seed=7 + 11 * fid + draw)
                del Xtr
                score = np.full(valid.shape, np.float32(0.0))
                cols = [feats[nm].reshape(-1) for nm in names]
                for s in range(0, q_idx.size, 400_000):
                    idx = q_idx[s:s + 400_000]
                    Xc = np.stack([c[idx] for c in cols], axis=1).astype(np.float32)
                    flat = score.reshape(-1)
                    flat[idx] = clf.predict_proba(Xc)[:, 1]
                emitB = emission.emit_B(score, valid, quadrant, known, budget)
                resB = dti_fold(emitB, sp.hidden & quadrant, valid, quadrant, known)
                binfo[arm] = {k: resB[k] for k in ("dti", "TPw", "FPw", "n_emitted")}
                del score, cols
            for arm in ("B1", "B2"):
                binfo[arm]["paired_delta"] = binfo[arm]["dti"] - binfo["B0"]["dti"]
            row["B"] = binfo
            results.append(row)
            print(f"draw={draw} fold={fid} A dTs: "
                  f"A1 {emit_info['A1']['paired_delta']:+.4f} (n {emit_info['A1']['n_emitted']:,}) A2 {emit_info['A2']['paired_delta']:+.4f} (n {emit_info['A2']['n_emitted']:,}) | "
                  f"B dTs: B1 {binfo['B1']['paired_delta']:+.4f} B2 {binfo['B2']['paired_delta']:+.4f}",
                  flush=True)
        if args.quick:
            break

    gate = {}
    for family, key in (("A", "A"), ("B", "B")):
        for arm in ([a for a in ("A1", "A2")] if family == "A" else ["B1", "B2"]):
            per_draw = {}
            for d in (0, 1) if not args.quick else (0,):
                deltas = [r[f"{{fam}}".format(fam=family)][arm]["paired_delta"]
                          for r in results if r["draw"] == d]
                per_draw[f"draw{d}"] = {"mean_delta": float(np.mean(deltas)),
                                        "positive_folds": int(np.sum(np.array(deltas) > 0)),
                                        "deltas": [float(x) for x in deltas]}
            ok_screen = all(v["mean_delta"] >= 0.005 and v["positive_folds"] >= 3
                             for v in per_draw.values()) if not args.quick else None
            confirm = None
            for d in (2, 3):
                k = f"draw{d}"
                if k in per_draw:
                    if per_draw[k]["mean_delta"] >= 0.005 and per_draw[k]["positive_folds"] >= 3:
                        confirm = k
            gate[arm] = {"screen_pass": bool(ok_screen) if ok_screen is not None else "quick-mode",
                          "confirm_draw": confirm, "per_draw": per_draw,
                          "PASS": (bool(ok_screen) and confirm is not None) if not args.quick else None}
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "runtime_s": time.time() - t0, "rows": results, "gate": gate,
           "protocol": "knowledge/01_preregistration_h29_worming_2026-10-03.md",
           "note": "all numbers are catalogue-internal proxy DTI, not live scores"}
    paths.EVIDENCE.mkdir(exist_ok=True)
    (paths.EVIDENCE / "h29_holdout.json").write_text(json.dumps(out, indent=2, default=float))
    (paths.EVIDENCE / "h29_gate.json").write_text(json.dumps(gate, indent=2, default=float))
    print(json.dumps(gate, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
