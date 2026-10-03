#!/usr/bin/env python3
"""Run the pre-registered spatial H29 screen, including the next H29-5 candidate.

Frozen H29-5 gate (knowledge/04): mean paired ΔDTI >= +0.005 and >=3/4 folds positive on both
screen draws (0,1), then the same threshold on at least one complete confirmation draw (2 or 3).
Additionally H29-5's delta is measured against the best same-fold/same-draw pre-existing control
among A0/A1/A2/B0/B1/B2. The default is screen-only; confirmation draws are fit only in a separate
`--confirmation-only` run after at least one arm passes its complete two-draw screen.

Usage: python scripts/run_holdout_screen.py [--quick | --screen-only | --confirmation-only | --reaggregate-existing]
`--quick` is a smoke test only (fold 0, draws 0-1); its gate is indeterminate and cannot pass.
`--screen-only` (also the safe default) evaluates both screen draws over four folds. A later
`--confirmation-only` appends confirmation draws 2/3 only if saved screen evidence has a passing arm;
otherwise it stops without fitting. `--reaggregate-existing` refreshes gate JSON from saved rows
without fitting models. All DTI values are catalogue-internal proxy metrics, not live/private scores.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems29 import emission, features, gating, gridio, head, holdout, paths  # noqa: E402
from gems29.metric import dti_binary  # noqa: E402


def load_inputs():
    with rasterio.open(paths.DATA / "bridge" / "sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    lab, _ = gridio.read_band(paths.DATA / "bridge" / "labels.tif")
    catalog = np.nan_to_num(lab) > 0
    parent, _ = gridio.read_band(paths.DATA / "inputs" / "h19_5_nan.tif")
    parent = emission.parent_solid_from_raster(parent, valid)
    return valid, catalog, parent


def load_feature_stack(valid):
    feats, _ = features.build_feature_dict(
        raw_path=paths.DATA / "bridge" / "training_features.tif",
        lidar_path=paths.DATA / "external" / "lidar_scarp_features_u8.tif",
        worm_dir=paths.DATA / "work" / "worming",
        known_catalog=np.zeros(valid.shape, bool), valid=valid)
    return feats


def arm_feature_sets(feats: dict) -> dict[str, list[str]]:
    worm_keys = [k for k in ("worm_mag_persist", "worm_grav_persist", "worm_joint_persist",
                             "worm_joint_defined") if k in feats]
    strength_keys = [k for k in ("worm_mag_strength_ratio", "worm_grav_strength_ratio",
                                 "worm_joint_strength_ratio") if k in feats]
    thermal_keys = [k for k in ("probe_dist_norm", "probe_dab", "probe_t2m_close") if k in feats]
    base = [k for k in feats if k.startswith(("raw_", "lid_", "dist_known"))]
    h29_5_keys = [k for k in ("h29_5_worm_strain", "h29_5_worm_dep_eq",
                              "h29_5_worm_ind_eq", "h29_5_corridor_interaction") if k in feats]
    if not h29_5_keys:
        raise ValueError("H29-5 interaction features were not constructed")
    return {
        "B0": base,
        "B1": base + worm_keys,
        "B2": base + thermal_keys,
        "B3": base + worm_keys + strength_keys + h29_5_keys,
    }


def add_thermal(feats: dict, valid: np.ndarray):
    zdir = paths.DATA / "gdr" / "probe" / "2m_temperature_probe_INGENIOUS_regional_data"
    shp = zdir / "2m_temperature_probe_n83geo" / "2m_temperature_probe_n83geo.shp"
    if not shp.exists():
        archive = paths.DATA / "gdr" / "2m_temperature_probe_INGENIOUS_regional_data.zip"
        if archive.exists():
            import zipfile
            extract_root = paths.DATA / "gdr" / "probe"
            root_resolved = extract_root.resolve()
            with zipfile.ZipFile(archive) as zf:
                for member in zf.infolist():
                    target = (extract_root / member.filename).resolve()
                    if not target.is_relative_to(root_resolved):
                        raise ValueError(f"unsafe path in probe archive: {member.filename}")
                zf.extractall(extract_root)
    if not shp.exists():
        print("thermal probes unavailable; B2 == B0 by construction")
        return
    for suffix in (".dbf", ".shx", ".prj"):
        if not shp.with_suffix(suffix).exists():
            raise FileNotFoundError(f"probe shapefile component missing: {shp.with_suffix(suffix)}")
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


def _atomic_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def aggregate_gates(results: list[dict]) -> dict:
    return {
        "A1": gating.gate_from_rows(results, family="A", arm="A1", delta_key="paired_delta"),
        "A2": gating.gate_from_rows(results, family="A", arm="A2", delta_key="paired_delta"),
        "B1": gating.gate_from_rows(results, family="B", arm="B1", delta_key="paired_delta"),
        "B2": gating.gate_from_rows(results, family="B", arm="B2", delta_key="paired_delta"),
        "H29-5": gating.gate_from_rows(results, family="B", arm="B3",
                                       delta_key="paired_delta_best_control"),
    }


def summarize_gate(results: list[dict], *, quick: bool = False) -> dict:
    """Compatibility summarizer for the archived four-arm gate reconciliation.

    The current H29/H29-5 runner and persisted gate use :func:`aggregate_gates` and the stricter
    unique-fold/finite-value checks. This helper reproduces the original A1/A2/B1/B2 summary schema
    so the preserved pre-correction reconciliation remains regression-testable.
    """
    out: dict[str, dict] = {}
    for family, arms in (("A", ("A1", "A2")), ("B", ("B1", "B2"))):
        for arm in arms:
            rows = [row for row in results if family in row and arm in row[family]]
            draw_ids = sorted({int(row["draw"]) for row in rows})
            per_draw: dict[str, dict] = {}
            for draw in draw_ids:
                cells = [row for row in rows if int(row["draw"]) == draw]
                deltas = [float(row[family][arm]["paired_delta"]) for row in cells]
                per_draw[f"draw{draw}"] = {
                    "mean_delta": float(np.mean(deltas)),
                    "positive_folds": int(np.sum(np.asarray(deltas) > 0.0)),
                    "n_folds": len(deltas),
                    "deltas": deltas,
                }
            if quick:
                out[arm] = {"screen_pass": "quick-mode", "confirm_draw": None,
                            "confirmation_eligible": False, "per_draw": per_draw, "PASS": None}
                continue
            screen_ok = all(
                f"draw{draw}" in per_draw
                and per_draw[f"draw{draw}"]["n_folds"] == 4
                and per_draw[f"draw{draw}"]["mean_delta"] + 1e-12 >= 0.005
                and per_draw[f"draw{draw}"]["positive_folds"] >= 3
                for draw in (0, 1)
            )
            confirm = next((f"draw{draw}" for draw in (2, 3)
                            if f"draw{draw}" in per_draw
                            and per_draw[f"draw{draw}"]["n_folds"] == 4
                            and per_draw[f"draw{draw}"]["mean_delta"] + 1e-12 >= 0.005
                            and per_draw[f"draw{draw}"]["positive_folds"] >= 3), None) if screen_ok else None
            out[arm] = {"screen_pass": bool(screen_ok), "confirm_draw": confirm,
                        "confirmation_eligible": bool(screen_ok), "per_draw": per_draw,
                        "PASS": bool(screen_ok and confirm is not None)}
    return out


def reaggregate_existing() -> int:
    """Refresh only the gate summary from saved fold rows; do not refit any models."""
    hold_path = paths.EVIDENCE / "h29_holdout.json"
    if not hold_path.is_file():
        raise FileNotFoundError(f"no saved holdout evidence at {hold_path}")
    out = json.loads(hold_path.read_text())
    rows = out.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("saved holdout evidence has no fold rows to aggregate")
    gate = aggregate_gates(rows)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out["gate"] = gate
    out["gate_reaggregated_utc"] = now
    run_mode = out.get("run_mode", "")
    if run_mode.startswith("quick"):
        out["confirmation_status"] = "not_run_quick_smoke"
    elif run_mode.startswith("screen-only"):
        out["confirmation_status"] = (
            "not_run_screen_failed_per_preregistered_compute_saver"
            if gate["H29-5"]["screen_pass"] is False else
            "required_in_followup_after_screen_pass"
        )
    else:
        out["confirmation_status"] = "evaluated_in_draws_2_and_3"
    _atomic_json(hold_path, out)
    _atomic_json(paths.EVIDENCE / "h29_gate.json", gate)
    print(json.dumps(gate, indent=2, allow_nan=False))
    print(f"reaggregated {len(rows)} saved rows without refitting")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--screen-only", action="store_true",
                      help="run both screen draws over four folds; this is also the safe default")
    mode.add_argument("--confirmation-only", action="store_true",
                      help="append confirmation draws only if saved screen evidence has a passing arm")
    mode.add_argument("--reaggregate-existing", action="store_true",
                      help="refresh gate JSON from saved holdout rows without refitting models")
    args = ap.parse_args()
    if args.reaggregate_existing:
        return reaggregate_existing()
    previous = None
    if args.confirmation_only:
        hold_path = paths.EVIDENCE / "h29_holdout.json"
        if not hold_path.is_file():
            raise FileNotFoundError("confirmation-only requires saved complete screen evidence")
        previous = json.loads(hold_path.read_text())
        if previous.get("protocol") != (
                "knowledge/01_preregistration_h29_worming_2026-10-03.md; "
                "knowledge/04_preregistered_next_hypothesis_slate_2026-10-03.md"):
            raise ValueError("saved screen evidence does not match the registered H29 protocol")
        if previous.get("run_mode", "").startswith("quick"):
            raise ValueError("a quick smoke test cannot authorize confirmation draws")
        prior_rows = previous.get("rows", [])
        if any(int(row.get("draw", -1)) in (2, 3) for row in prior_rows):
            raise ValueError("confirmation draws already exist; use --reaggregate-existing instead")
        prior_gate = aggregate_gates(prior_rows)
        passing_arms = [arm for arm, summary in prior_gate.items()
                        if summary.get("screen_pass") is True]
        if not passing_arms:
            print("No arm passed both complete screen draws; confirmation model fits skipped.")
            return 0
        print("confirmation authorized by screen pass for:", ", ".join(passing_arms))
    t0 = time.time()
    valid, catalog, parent = load_inputs()
    folds = holdout.make_quadrant_folds(valid)
    feats = load_feature_stack(valid)
    add_thermal(feats, valid)
    interaction_names = features.add_h29_5_interactions(feats, valid)
    armsets = arm_feature_sets(feats)
    worm_dir = paths.DATA / "work" / "worming"
    with rasterio.open(worm_dir / "worm_joint_persist.tif") as ds:
        jointP = np.nan_to_num(ds.read(1))
    with rasterio.open(worm_dir / "worm_joint_defined.tif") as ds:
        jointDef = np.nan_to_num(ds.read(1))
    joint = {"P": jointP, "defined": jointDef}
    lidar = {k: feats[k] for k in feats if k.startswith("lid_")}

    draws = [2, 3] if args.confirmation_only else [0, 1]
    fold_ids = [0] if args.quick else [0, 1, 2, 3]
    results = list(previous.get("rows", [])) if previous is not None else []
    for draw in draws:
        for fid in fold_ids:
            sp = holdout.make_split(catalog, folds, fid, draw)
            known = catalog & ~sp.hidden
            dist = distance_transform_edt(~known) - 1.0
            d = np.clip(dist, 0, 30)
            feats["dist_known_px_norm"] = (d / 30.0).astype(np.float32)
            feats["dist_known_collapse"] = np.exp(-d / 4.0).astype(np.float32)
            quadrant = sp.fold_mask
            # ---- Matched-budget, no-head emission arms ----
            A = {arm: emission.emit_A(parent, valid, quadrant, known, joint, lidar, arm)
                 for arm in ("A0", "A1", "A2")}
            # ---- Train outside held-out quadrant plus fixed guard ----
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
            emit_info = {}
            for arm, emitted in A.items():
                res = dti_fold(emitted, sp.hidden & quadrant, valid, quadrant, known)
                emit_info[arm] = {k: res[k] for k in ("dti", "TPw", "FPw", "n_emitted")}
            for arm in ("A1", "A2"):
                emit_info[arm]["paired_delta"] = emit_info[arm]["dti"] - emit_info["A0"]["dti"]
            row["A"] = emit_info

            # ---- Dense head arms ----
            binfo = {}
            budget = int(A["A0"].sum())
            for arm in ("B0", "B1", "B2", "B3"):
                names = armsets[arm]
                Xtr = np.stack([feats[nm].reshape(-1)[rowset] for nm in names], axis=1).astype(np.float32)
                clf = head.fit_head(Xtr, ytr, seed=7 + 11 * fid + draw)
                del Xtr
                score = np.zeros(valid.shape, np.float32)
                cols = [feats[nm].reshape(-1) for nm in names]
                flat = score.reshape(-1)
                for s in range(0, q_idx.size, 400_000):
                    idx = q_idx[s:s + 400_000]
                    Xc = np.stack([c[idx] for c in cols], axis=1).astype(np.float32)
                    flat[idx] = clf.predict_proba(Xc)[:, 1]
                emitB = emission.emit_B(score, valid, quadrant, known, budget)
                resB = dti_fold(emitB, sp.hidden & quadrant, valid, quadrant, known)
                binfo[arm] = {k: resB[k] for k in ("dti", "TPw", "FPw", "n_emitted")}
                del score, cols, clf
            for arm in ("B1", "B2", "B3"):
                binfo[arm]["paired_delta"] = binfo[arm]["dti"] - binfo["B0"]["dti"]
            controls = {**emit_info, **{k: v for k, v in binfo.items() if k in ("B0", "B1", "B2")}}
            best_name, best_metric = max(controls.items(), key=lambda kv: kv[1]["dti"])
            binfo["B3"]["best_control_arm"] = best_name
            binfo["B3"]["best_control_dti"] = float(best_metric["dti"])
            binfo["B3"]["paired_delta_best_control"] = float(binfo["B3"]["dti"] - best_metric["dti"])
            binfo["B3"]["paired_delta_A0"] = float(binfo["B3"]["dti"] - emit_info["A0"]["dti"])
            row["B"] = binfo
            row["candidate"] = {"id": "H29-5", "features": interaction_names,
                                "budget_pixels": budget, "best_control_arm": best_name}
            results.append(row)
            print(f"draw={draw} fold={fid} best={best_name} "
                  f"A1 {emit_info['A1']['paired_delta']:+.4f} A2 {emit_info['A2']['paired_delta']:+.4f} | "
                  f"B1 {binfo['B1']['paired_delta']:+.4f} B2 {binfo['B2']['paired_delta']:+.4f} "
                  f"H29-5 vs B0 {binfo['B3']['paired_delta']:+.4f} "
                  f"vs best {binfo['B3']['paired_delta_best_control']:+.4f}", flush=True)

    gate = aggregate_gates(results)
    any_screen_pass = any(summary.get("screen_pass") is True for summary in gate.values())
    all_screens_failed = all(summary.get("screen_pass") is False for summary in gate.values())
    confirmation_status = (
        "not_run_quick_smoke" if args.quick else
        "evaluated_in_draws_2_and_3" if args.confirmation_only else
        "required_in_followup_after_screen_pass" if any_screen_pass else
        "not_run_screen_failed_per_preregistered_compute_saver" if all_screens_failed else
        "not_run_screen_incomplete")
    run_mode = ("quick-smoke-test-not-eligible" if args.quick else
                "confirmation-only-4-fold-2-draw-appended-to-passing-screen" if args.confirmation_only else
                "screen-only-4-fold-2-draw; confirmation conditional on screen pass")
    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_s": time.time() - t0,
        "run_mode": run_mode,
        "rows": results,
        "gate": gate,
        "confirmation_status": confirmation_status,
        "confirmation_screen_evidence_generated_utc": previous.get("generated_utc") if previous else None,
        "protocol": "knowledge/01_preregistration_h29_worming_2026-10-03.md; knowledge/04_preregistered_next_hypothesis_slate_2026-10-03.md",
        "candidate": {"id": "H29-5", "name": "persistent basement corridor × deformation/seismicity",
                      "feature_set": armsets["B3"], "interaction_features": interaction_names,
                      "control_rule": "best same-fold/same-draw DTI among A0/A1/A2/B0/B1/B2",
                      "note": "screening is catalogue-internal proxy evidence only"},
        "note": "All numbers are catalogue-internal proxy DTI, not live or private leaderboard scores. Owner-mirror inputs are not organizer-authenticated.",
    }
    paths.EVIDENCE.mkdir(exist_ok=True)
    _atomic_json(paths.EVIDENCE / "h29_holdout.json", out)
    _atomic_json(paths.EVIDENCE / "h29_gate.json", gate)
    print(json.dumps(gate, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
