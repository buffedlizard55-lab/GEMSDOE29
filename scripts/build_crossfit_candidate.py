#!/usr/bin/env python3
"""Cross-fitted candidate builder: leak-free habitat scores for C0 and the A4_h41_union arm.

Why this script exists (verified defect in the previous artifact path)
---------------------------------------------------------------------
``scripts/build_repo_candidate.py`` trains its artifact model on *every* catalogue pixel while the
catalogue family ``E`` is built from that same full catalogue. ``E``'s first column is
``log1p(min(distance_to_nearest_catalogue_pixel, 60))`` (``src/gemsdoe/features.py``,
``build_catalogue_features``), which is **exactly 0.0 for every positive** and ``>= 1.0986`` for every
sampled negative. Measured on the restored data (2026-10-03, draws-free):

* train AUC of the 81-column artifact model = **1.0**;
* tree 1's root split is ``E_dist`` at threshold ``0.0``;
* across all 100 trees only **2 of 81** columns are ever used (``E_dist`` 100 splits, ``mag_anom`` 200);
* adding the five H41 columns changes nothing: **0 splits** land on them and the emitted mask is
  **byte-identical** (sha256 ``3537e9fc47a46503…``), which is how the defect was found.

So the headline download was a distance-to-catalogue look-up, not a habitat model. The screen protocol
never had this problem: ``Cell`` builds ``E`` from ``draw.visible``, which has the hidden components
removed, so the screen numbers in ``evidence/h41_screen/`` stand.

What this script does differently
---------------------------------
Train exactly like the validated cells do — per (fold, draw), ``E``/tip/H41 built from ``draw.visible``,
positives = ``draw.hidden_train``, negatives = <=300k non-catalogue pixels >1.5 px away — then **apply**
each trained model to the *whole* footprint with ``E`` built from the full catalogue. Using the full
catalogue at prediction time is legitimate (the catalogue is a supplied input to the competition task);
what was broken was letting it separate the training labels perfectly. Predictions are averaged over
cells, then the frozen emission runs (Hessian ridge NMS -> drop catalogue -> top K = 2.45% ->
score-ordered Poisson-disk dots at 2.4 px).

Both arms are built in the same pass so the C0/A4 difference is attributable to the H41 columns alone.
The script prints how many tree splits land on the H41 columns and refuses to continue if that count is
zero — the degeneracy guard that ``build_repo_candidate.py`` lacks.

    GEMS_DATA_DIR=$PWD/data python3 scripts/build_crossfit_candidate.py

Never contacts DrivenData.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import (  # noqa: E402
    HGB_PARAMS,
    N_NEG,
    Context,
    gather_columns,
    load_context,
)
from gemsdoe.features import build_catalogue_features, build_tip_continuation  # noqa: E402
from gemsdoe.h35 import _trace_grids  # noqa: E402
from gemsdoe.h41 import (  # noqa: E402
    H41_NAMES,
    H41_PARAMS,
    build_h41_fields,
    degenerate_fields,
    parse_centroids,
)
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.submission import (  # noqa: E402
    content_id,
    make_note,
    sha256_file,
)
from gemsdoe.thinning import ridge_nms, score_ordered_dots, select_top_positive  # noqa: E402

# gems29.submission.write_submission is the repo's full variant writer: it emits the NaN-outside TIFF,
# the ZERO-outside TIFF and the one-TIFF ZIP, then reads all three back and raises if any local format
# check fails. The zero-outside twin matters: a portal that range-checks the *whole* array rejects NaN,
# which is the "Predicted values must be in range [0, 1]" failure the owner reported (IR-PORTAL-01).
from gems29.submission import write_submission as write_all_variants  # noqa: E402

K_FRAC = 0.0245
MIN_DIST_PX = 2.4
NMS_SIGMA = 1.0
NEG_BUFFER_PX = 1.5
MIN_NONZERO_FRACTION = 0.002
CHUNK = 250_000
FOLDS = ("NW", "NE", "SW", "SE")
DEFAULT_DRAWS = (30, 31)          # the stage that validated A4_h41_union
ARMS = ("C0_base", "A4_h41_union")
ARM_COLUMNS = {"C0_base": [], "A4_h41_union": list(range(len(H41_NAMES)))}
QFAULTS_CSV = "external/gdr_qfaults_traces.csv"
HOLDOUT_BEST = 0.14479018210246675
SCREEN_GAIN = {"C0_base": 0.0, "A4_h41_union": 0.0073436}
CONFIRM_GAIN = {"C0_base": 0.0, "A4_h41_union": 0.0077283}


def git_state() -> dict:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, branch, dirty = "unknown", "unknown", True
    return {"revision": revision, "branch": branch, "dirty_worktree": dirty}


def scarp_strike_grid(ctx: Context) -> tuple[np.ndarray, np.ndarray]:
    H, W = ctx.foot.shape
    g = np.zeros((H, W), np.float32)
    g.ravel()[ctx.fi] = np.nan_to_num(ctx.h27_scarp, nan=0.0, posinf=0.0, neginf=0.0)
    cos2t, sin2t, _ = _trace_grids(g)
    return cos2t, sin2t


def assemble(ctx: Context, E: np.ndarray, tip: np.ndarray, idx: np.ndarray,
             h41: np.ndarray | None) -> np.ndarray:
    """static + E + add-on extras + H27 (tip, scarp, tip*scarp) [+ 5 H41 columns]."""
    ns = ctx.static.shape[0]
    ne = E.shape[0]
    n_extra = len(ctx.extra_names)
    n_h27 = 3
    n_h41 = len(H41_NAMES) if h41 is not None else 0
    X = np.empty((idx.size, ns + ne + n_extra + n_h27 + n_h41), np.float32)
    gather_columns(ctx, E, idx, extras=True, out=X)
    j = ns + ne + n_extra
    scarp = ctx.h27_scarp[idx]
    X[:, j] = tip[idx]
    X[:, j + 1] = scarp
    X[:, j + 2] = tip[idx] * scarp
    if h41 is not None:
        X[:, j + n_h27:] = h41[:, idx].T
    return X


def base_column_names(ctx: Context, E: np.ndarray) -> list[str]:
    return (list(ctx.static_names) + list(ctx.e_names) + list(ctx.extra_names) + ctx.h27_names)


def load_mask_from_tif(path: Path) -> np.ndarray:
    """Recover a boolean emission mask from a published NaN-outside candidate.

    Used only by ``--repackage``: the in-footprint values of a verified ``-nan.tif`` are exactly 0.0/1.0,
    so the mask is recoverable without refitting. Anything else is refused rather than rounded away.
    """
    import rasterio

    if not path.is_file():
        raise SystemExit(f"--repackage source not found: {path}")
    with rasterio.open(path) as ds:
        if ds.count != 1 or ds.dtypes[0] != "float32":
            raise SystemExit(f"{path} is not a single-band float32 GeoTIFF")
        arr = ds.read(1)
    foot = np.isfinite(arr)
    inside = arr[foot]
    if not np.isin(inside, (0.0, 1.0)).all():
        raise SystemExit(f"{path} has in-footprint values other than 0.0/1.0; refusing to repackage")
    return arr > 0.5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draws", default=",".join(str(d) for d in DEFAULT_DRAWS))
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    parser.add_argument("--record", type=Path, default=ROOT / "evidence" / "crossfit_candidate_build.json")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    parser.add_argument("--repackage", nargs=2, metavar=("C0_TIF", "A4_TIF"), default=None,
                        help="Recover the two emission masks from already-published -nan.tif candidates and "
                             "rewrite every variant + format receipt without refitting. Emission, guards and "
                             "the degeneracy checks are skipped; nothing is recomputed from the features.")
    args = parser.parse_args()
    draws = [int(d) for d in args.draws.split(",") if d.strip()]
    if not draws:
        parser.error("at least one draw is required")

    data, work = data_dir(), work_dir()
    template, labels_path = data / "sample_submission.tif", data / "labels.tif"
    qfaults = data / QFAULTS_CSV
    for path in (template, labels_path, qfaults):
        if not path.is_file():
            parser.error(f"missing hash-pinned input {path}; run scripts/restore_h31_data.py --group all first")
    promotion = ROOT / "evidence" / "h41_screen" / "promotion_gate.json"
    gate = json.loads(promotion.read_text()) if promotion.is_file() else {}
    a4_gate = gate.get("arms", {}).get("A4_h41_union", {})

    from sklearn.ensemble import HistGradientBoostingClassifier

    t_all = time.time()
    ctx = load_context(work)
    args.from_tif = ({ARMS[0]: Path(args.repackage[0]), ARMS[1]: Path(args.repackage[1])}
                     if args.repackage else None)
    prob = {arm: np.zeros(ctx.fi.size, np.float64) for arm in ARMS}
    cells: list[dict] = []
    h41_split_total = 0
    diag_full: dict = {}

    if not args.from_tif:
        cfield = parse_centroids(qfaults, shape=ctx.foot.shape)
        cos2t, sin2t = scarp_strike_grid(ctx)

        # Prediction-time catalogue features use the FULL supplied catalogue (legitimate: the catalogue is
        # an input to the task). Training-time features use draw.visible, which hides recovered components.
        E_full = build_catalogue_features(ctx.labels, ctx.fi)
        tip_full = build_tip_continuation(ctx.labels, ctx.foot, ctx.fi)
        h41_full, diag_full = build_h41_fields(
            cfield, visible=ctx.labels, footprint=ctx.foot, footprint_idx=ctx.fi,
            scarp_vec=ctx.h27_scarp, cos2t=cos2t, sin2t=sin2t)
        problems = degenerate_fields(h41_full, min_nonzero_fraction=MIN_NONZERO_FRACTION)
        if problems:
            raise SystemExit("H41 viability guard failed: " + "; ".join(problems))

        names = base_column_names(ctx, E_full)
        n_base = len(names)
        col_of = {n: i for i, n in enumerate(names + list(H41_NAMES))}

    for fold in range(0 if args.from_tif else len(FOLDS)):
        for seed in draws:
            d = ctx.holdout.draw(fold, seed)
            E_vis = build_catalogue_features(d.visible, ctx.fi)
            tip_vis = build_tip_continuation(d.visible, ctx.foot, ctx.fi)
            h41_vis, _ = build_h41_fields(
                cfield, visible=d.visible, footprint=ctx.foot, footprint_idx=ctx.fi,
                scarp_vec=ctx.h27_scarp, cos2t=cos2t, sin2t=sin2t)
            rng = np.random.default_rng(777 + 31 * fold + seed)   # identical to Cell.__init__
            pos = ctx.vec(d.hidden_train)
            near = distance_transform_edt(~d.hidden_train) <= NEG_BUFFER_PX
            cand = ctx.vec(d.train_region & ~ctx.labels & ~near)
            neg = rng.choice(cand, size=min(N_NEG, cand.size), replace=False)
            idx = np.sort(np.concatenate([pos, neg]))
            y = np.isin(idx, pos).astype(np.int8)
            Xtr = assemble(ctx, E_vis, tip_vis, idx, h41_vis)
            cell = dict(fold=FOLDS[fold], fold_index=fold, draw=seed, train_rows=int(idx.size),
                        positives=int(y.sum()), columns=int(Xtr.shape[1]))
            models: dict[str, object] = {}
            colsets: dict[str, list[int]] = {}
            for arm in ARMS:
                cols = [col_of[n] for n in names] + [n_base + i for i in ARM_COLUMNS[arm]]
                colsets[arm] = cols
                t0 = time.time()
                model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
                model.fit(np.ascontiguousarray(Xtr[:, cols]), y)
                fit_s = time.time() - t0
                arm_names = [names[c] for c in cols if c < n_base] + [H41_NAMES[i] for i in ARM_COLUMNS[arm]]
                used: dict[str, int] = {}
                for stage in model._predictors:
                    for predictor in stage:
                        for f in predictor.nodes["feature_idx"]:
                            used[arm_names[f]] = used.get(arm_names[f], 0) + 1
                n_h41_splits = sum(v for k, v in used.items() if k in H41_NAMES)
                h41_split_total += n_h41_splits
                models[arm] = model
                cell[arm] = dict(fit_s=fit_s, features_used=len(used), h41_splits=n_h41_splits,
                                 top_features=sorted(used.items(), key=lambda kv: -kv[1])[:5])
                print(f"fold={FOLDS[fold]} draw={seed} arm={arm}: fit {fit_s:.1f}s, "
                      f"{len(used)} features used, H41 splits={n_h41_splits}", flush=True)
            # One assembled chunk serves every arm, so the prediction-time matrix is built once per chunk.
            for start in range(0, ctx.fi.size, CHUNK):
                rows = np.arange(start, min(start + CHUNK, ctx.fi.size))
                Xq = assemble(ctx, E_full, tip_full, rows, h41_full)
                for arm in ARMS:
                    prob[arm][rows] += models[arm].predict_proba(
                        np.ascontiguousarray(Xq[:, colsets[arm]]))[:, 1]
                del Xq
            print(f"fold={FOLDS[fold]} draw={seed}: full-footprint prediction done", flush=True)
            cells.append(cell)
            del Xtr

    if not args.from_tif:
        prob = {arm: (p / float(len(FOLDS) * len(draws))).astype(np.float32) for arm, p in prob.items()}
    if h41_split_total == 0 and not args.from_tif:
        raise SystemExit(
            "degeneracy guard: no tree split in any cell used an H41 column, so the A4 arm would be "
            "indistinguishable from C0. Refusing to write a candidate that does not implement its own method.")

    artifacts: dict[str, dict] = {}
    for arm in ARMS:
        if args.from_tif:
            emitted = load_mask_from_tif(args.from_tif[arm])
        else:
            grid = np.zeros(ctx.foot.shape, np.float32)
            grid.ravel()[ctx.fi] = prob[arm]
            s = grid.copy()
            ridge = ridge_nms(s, ctx.foot, NMS_SIGMA)
            scored = np.where(ridge & ~ctx.labels, s, 0.0)
            k = int(round(K_FRAC * int(ctx.foot.sum())))
            candidates = select_top_positive(scored, ctx.foot, k)
            emitted = score_ordered_dots(s, candidates, MIN_DIST_PX)
        n_dots = int(emitted.sum())
        if n_dots == 0:
            raise SystemExit(f"{arm}: emission produced no dots")
        cid = content_id(emitted, ctx.foot, ctx.labels)
        slug = "xfit-h41-union-qfaults" if arm == "A4_h41_union" else "xfit-c0-habitat"
        stem = f"gemsdoe29-{slug}-{args.date}-{cid}"
        nan_path = args.out_dir / f"{stem}-nan.tif"
        if nan_path.exists():
            raise SystemExit(f"refusing to overwrite existing candidate {nan_path}")
        note = make_note(
            "H41 union xfit" if arm == "A4_h41_union" else "C0 habitat xfit",
            ("cross-fitted, leak-free; G1+G2 pass, G3 proxy conflict" if arm == "A4_h41_union"
             else "cross-fitted leak-free control arm; comparison baseline"),
            cid, scored="unscored")
        # Writes -nan.tif, -zeros.tif, -nan.zip and checks-<stem>.json; raises if any check fails.
        args.out_dir.mkdir(parents=True, exist_ok=True)
        write_all_variants(emitted, args.out_dir, stem, note=note)
        near_vis = distance_transform_edt(~ctx.labels) <= 3
        files = {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
                 for p in sorted(args.out_dir.glob(f"{stem}-*"))}
        artifacts[arm] = {
            "stem": stem, "file": f"{stem}-nan.tif", "path": nan_path.relative_to(ROOT).as_posix(),
            "zeros_file": f"{stem}-zeros.tif", "zeros_path": (args.out_dir / f"{stem}-zeros.tif").relative_to(ROOT).as_posix(),
            "zip": f"{stem}-nan.zip", "files": files,
            "bytes": nan_path.stat().st_size, "sha256": sha256_file(nan_path), "content_id": cid,
            "positive_pixels": n_dots, "note": note, "note_characters": len(note),
            "format_receipt": f"docs/downloads/checks-{stem}.json",
            "on_catalogue_pixels": int((emitted & ctx.labels).sum()),
            "hug_share_within_300m_of_catalogue": float((emitted & near_vis).sum() / max(n_dots, 1)),
        }
        if not args.from_tif:
            artifacts[arm]["mean_probability"] = float(prob[arm].mean())
            artifacts[arm]["max_probability"] = float(prob[arm].max())
        print(f"{arm}: {n_dots:,} dots -> {stem}-nan.tif (+ -zeros.tif, .zip, format receipt)")

    base, a4 = artifacts["C0_base"], artifacts["A4_h41_union"]
    if base["content_id"] == a4["content_id"]:
        raise SystemExit("the two arms produced identical masks; the H41 columns are still inert")

    # In --repackage mode the fitting diagnostics already live in the record; keep them and replace only
    # the artifact block, so the H41 split counts survive a variant rewrite.
    prior = json.loads(args.record.read_text()) if (args.from_tif and args.record.is_file()) else None
    record = prior if prior else {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": ("Leak-free cross-fitted artifacts. Replaces the degenerate single-fit path in "
                    "scripts/build_repo_candidate.py, whose E_dist column separated the training labels "
                    "perfectly (train AUC 1.0) and used 2 of 81 columns."),
        "protocol": {
            "training": "per (fold, draw): E/tip/H41 from draw.visible, positives = draw.hidden_train, "
                        "negatives <= 300k non-catalogue pixels > 1.5 px away, rng seed 777+31*fold+draw",
            "prediction": "whole footprint with E/tip/H41 built from the FULL supplied catalogue, "
                          "then averaged over all cells",
            "folds": list(FOLDS), "draws": draws, "cells_per_arm": len(FOLDS) * len(draws),
            "model": "HistGradientBoostingClassifier",
            "parameters": {k: (dict(v) if isinstance(v, dict) else v) for k, v in HGB_PARAMS.items()},
            "emission": {"ridge_nms_sigma_px": NMS_SIGMA, "k_fraction_of_footprint": K_FRAC,
                         "min_distance_px": MIN_DIST_PX,
                         "policy": "score-ordered Poisson disk (frozen H34 C0 / H41 standard emission)"},
            "h41_params": {k: float(v) for k, v in H41_PARAMS.items()},
            "h41_diagnostics_full_catalogue": diag_full,
        },
        "degeneracy_guard": {
            "h41_split_total": h41_split_total,
            "per_cell": [{**{k: c[k] for k in ("fold", "draw")},
                          "C0_base": c["C0_base"], "A4_h41_union": c["A4_h41_union"]} for c in cells],
            "rule": "abort if no tree split in any cell lands on an H41 column",
        },
        "evidence_for_method": {
            "screen": "evidence/h41_screen/ (draws 28/29, 40 cells)",
            "confirmation": "evidence/h41_screen/ (draws 30/31, 40 cells)",
            "preregistration": "knowledge/24_preregistered_h41_screen_2026-10-03.md",
            "results_writeup": "knowledge/26_h41_results_2026-10-03.md",
            "screen_mean_paired_dti_gain": SCREEN_GAIN,
            "confirmation_mean_paired_dti_gain": CONFIRM_GAIN,
            "holdout_best": HOLDOUT_BEST,
            "G1_screen_pass": a4_gate.get("G1_screen_pass"),
            "G2_confirmation_pass": a4_gate.get("G2_confirmation_pass"),
            "g3_secondary_proxy": {
                "rule": gate.get("rule"),
                "G3_ELIGIBLE": a4_gate.get("G3_ELIGIBLE"),
                "sgmc_positive_folds_screen": a4_gate.get("sgmc", {}).get("screen"),
                "sgmc_positive_folds_confirm": a4_gate.get("sgmc", {}).get("confirm"),
                "sgmc_mean_gain_screen": a4_gate.get("sgmc", {}).get("mean_gain_screen"),
                "sgmc_mean_gain_confirm": a4_gate.get("sgmc", {}).get("mean_gain_confirm"),
            },
            "proxy_caveat": ("DTI values are catalogue-gap proxies on spatially blocked folds, not official "
                             "competition scores. This artifact is cross-fitted, so no proxy score is quoted "
                             "for the artifact itself."),
        },
        "artifacts": artifacts,
        "inputs": {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                   for p in (labels_path, template, qfaults)},
        "git": git_state(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "total_seconds": time.time() - t_all,
        "provenance_warning": ("Owner-mirror inputs are byte-verified but not organizer-authenticated; these "
                               "are research candidates, not official scores, and no weekly slot is approved."),
    }
    record["artifacts"] = artifacts
    record["repackaged_utc"] = datetime.now(timezone.utc).isoformat() if args.from_tif else None
    record["repackaged_from"] = ({arm: str(args.from_tif[arm]) for arm in ARMS}
                                 if args.from_tif else None)
    if prior:
        record["protocol"].setdefault("note", "artifacts rewritten in --repackage mode; fitting diagnostics preserved")
        record["total_seconds"] = prior.get("total_seconds")
    else:
        record["degeneracy_guard"]["per_cell"] = [
            {**{k: c[k] for k in ("fold", "draw")}, "C0_base": c["C0_base"], "A4_h41_union": c["A4_h41_union"]}
            for c in cells]
        record["total_seconds"] = time.time() - t_all
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2, default=float) + "\n")
    if args.from_tif:
        print(f"repackaged; fitting diagnostics preserved from the prior record "
              f"(H41 splits then: {record.get('degeneracy_guard', {}).get('h41_split_total', 'n/a')})")
    else:
        print(f"H41 splits across all cells: {h41_split_total:,}")
    print(f"wrote {args.record}")
    for arm in ARMS:
        print(f"note [{arm}]: {artifacts[arm]['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
