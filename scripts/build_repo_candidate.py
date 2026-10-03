#!/usr/bin/env python3
"""Build the repository's own candidate submission GeoTIFF.

.. warning::
   **Do not use this script to produce a new artifact.** Measured on the restored data (2026-10-03),
   the model it fits separates its own training labels perfectly: it builds catalogue family ``E`` from
   the same full catalogue its positives come from, and ``E``'s first column
   ``log1p(min(distance_to_nearest_catalogue_pixel, 60))`` is exactly ``0.0`` on all 60,988 positives and
   ``>= 1.098612`` on all sampled negatives. Train AUC is 1.0, tree 1's root split is that column at
   threshold 0.0, and only **2 of 81** columns are ever used across all 100 trees. Appending new physics
   columns changes nothing: 0 splits land on them and the emitted mask stays byte-identical
   (sha256 ``3537e9fc47a46503…``). The screens in ``evidence/`` are unaffected because ``Cell`` builds
   ``E`` from ``draw.visible`` with the hidden components removed. Use
   ``scripts/build_crossfit_candidate.py`` instead, which trains the way the validated cells do and
   guards against an inert feature block. See ``knowledge/33_artifact_leakage_and_crossfit_2026-10-03.md``
   and ``IR-29-ARTIFACT-LEAK``.

The candidate implements the method that is validated on the spatially blocked hide-and-recover
holdout by the H34 screen controls (`evidence/h34_coverage_screen/`, draws 20/21, four quadrants):
a HistGradientBoosting habitat model over the full feature matrix used in that screen, followed by
the frozen standard emission (Hessian ridge NMS -> drop known catalogue -> top K = 2.45% of the
scored footprint -> score-ordered Poisson-disk dots at 2.4 px).

Training for the *artifact* uses every catalogue pixel (that is what a submission should do); the
holdout evidence for the method comes from the per-fold screen, where each model was trained with
the hidden components removed. Because the artifact's model has seen the catalogue, its own
holdout score would be contaminated and is deliberately not computed or quoted anywhere.

This script never contacts DrivenData and asserts no organizer acceptance. The output is a research
candidate that is byte-verified against the restored owner-mirror template.
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
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.experiment import HGB_PARAMS, N_NEG, Context, gather_columns, load_context  # noqa: E402
from gemsdoe.features import build_catalogue_features, build_tip_continuation  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.submission import content_id, make_filename, make_note, sha256_file, write_submission, zip_single  # noqa: E402
from gemsdoe.thinning import ridge_nms, score_ordered_dots, select_top_positive  # noqa: E402

K_FRAC = 0.0245
MIN_DIST_PX = 2.4
NMS_SIGMA = 1.0
DEFAULT_SEEDS = (0, 1, 2)
NEAR_LABEL_PX = 1.5
CHUNK = 250_000


def git_state() -> dict:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, branch, dirty = "unknown", "unknown", True
    return {"revision": revision, "branch": branch, "dirty_worktree": dirty}


def training_sample(ctx: Context, seed: int = 777):
    """Positives = every catalogue pixel; negatives = <=N_NEG non-catalogue pixels >1.5 px away."""
    rng = np.random.default_rng(seed)
    pos = ctx.vec(ctx.labels)
    near = distance_transform_edt(~ctx.labels) <= NEAR_LABEL_PX
    cand = ctx.vec(ctx.foot & ~ctx.labels & ~near)
    neg = rng.choice(cand, size=min(N_NEG, cand.size), replace=False)
    idx = np.sort(np.concatenate([pos, neg]))
    y = np.isin(idx, pos).astype(np.int8)
    return idx, y


def full_matrix(ctx: Context, idx: np.ndarray) -> np.ndarray:
    """The exact column layout of ``Cell(..., extras=True, h27=True)`` for arbitrary footprint rows."""
    ns, ne = ctx.static.shape[0], ctx.E.shape[0]
    n_extra = len(ctx.extra_names)
    X = np.empty((idx.size, ns + ne + n_extra + 3), np.float32)
    gather_columns(ctx, ctx.E, idx, extras=True, out=X)
    tip = ctx.tip[idx]
    scarp = ctx.h27_scarp[idx]
    X[:, ns + ne + n_extra] = tip
    X[:, ns + ne + n_extra + 1] = scarp
    X[:, ns + ne + n_extra + 2] = tip * scarp
    return X


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    parser.add_argument("--record", type=Path, default=ROOT / "evidence" / "repo_candidate_build.json")
    parser.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS))
    parser.add_argument("--slug", default="repo-c0-habitat-emission")
    args = parser.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        parser.error("at least one model seed is required")

    data = data_dir()
    work = work_dir()
    template = data / "sample_submission.tif"
    labels_path = data / "labels.tif"
    for path in (template, labels_path):
        if not path.is_file():
            parser.error(f"missing hash-pinned input {path}; restore the core inputs first")

    ctx = load_context(work)
    # Artifact configuration: catalogue features built from the full supplied catalogue.
    ctx.E = build_catalogue_features(ctx.labels, ctx.fi)
    ctx.tip = build_tip_continuation(ctx.labels, ctx.foot, ctx.fi)

    idx, y = training_sample(ctx)
    Xtr = full_matrix(ctx, idx)
    print(f"training rows {idx.size:,} (positives {int(y.sum()):,}); feature columns {Xtr.shape[1]}")

    from sklearn.ensemble import HistGradientBoostingClassifier

    probabilities = np.zeros(ctx.fi.size, np.float64)
    fit_seconds: list[float] = []
    for seed in seeds:
        model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
        t0 = time.time()
        model.fit(Xtr, y)
        fit_seconds.append(time.time() - t0)
        for start in range(0, ctx.fi.size, CHUNK):
            rows = np.arange(start, min(start + CHUNK, ctx.fi.size))
            probabilities[rows] += model.predict_proba(full_matrix(ctx, rows))[:, 1]
        print(f"seed {seed}: fit {fit_seconds[-1]:.1f}s, cumulative chunk prediction done", flush=True)
    probabilities /= float(len(seeds))
    del Xtr

    grid = np.zeros(ctx.foot.shape, np.float32)
    grid.ravel()[ctx.fi] = probabilities.astype(np.float32)
    s = grid.copy()
    ridge = ridge_nms(s, ctx.foot, NMS_SIGMA)
    scored = np.where(ridge & ~ctx.labels, s, 0.0)
    k = int(round(K_FRAC * int(ctx.foot.sum())))
    candidates = select_top_positive(scored, ctx.foot, k)
    emitted = score_ordered_dots(s, candidates, MIN_DIST_PX)
    n_dots = int(emitted.sum())
    print(f"candidates {int(candidates.sum()):,} of K={k:,}; emitted dots {n_dots:,}")
    if n_dots == 0:
        raise SystemExit("emission produced no dots; refusing to write an empty candidate")

    pred = np.where(emitted, np.float32(1.0), np.float32(0.0))
    cid = content_id(pred, ctx.foot, ctx.labels)
    name = make_filename(args.slug, datetime.now(timezone.utc).strftime("%Y%m%d"), cid, "nan")
    out_path = args.out_dir / name
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing candidate {out_path}")
    write_submission(pred, template, out_path)
    zpath = zip_single(out_path)
    note = make_note("repo candidate", "HGB habitat + frozen standard emission; proxy-validated on the blocked holdout; unscored", cid)
    record = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": {
            "model": "HistGradientBoostingClassifier",
            "parameters": {k: (dict(v) if isinstance(v, dict) else v) for k, v in HGB_PARAMS.items()},
            "model_seeds": seeds,
            "fit_seconds": fit_seconds,
            "training_rows": int(idx.size),
            "training_positives": int(y.sum()),
            "negative_sampling": f"<= {N_NEG:,} non-catalogue footprint pixels > {NEAR_LABEL_PX} px from any catalogue pixel",
            "feature_layout": "static A-D + catalogue family E + add-on extras + H27 tip/scarp/interaction (as H34 controls)",
            "emission": {
                "ridge_nms_sigma_px": NMS_SIGMA,
                "k_fraction_of_footprint": K_FRAC,
                "k_candidates": k,
                "min_distance_px": MIN_DIST_PX,
                "policy": "score-ordered Poisson disk (H34 C0 / H31 frozen standard emission)",
            },
        },
        "evidence_for_method": {
            "screen": "evidence/h34_coverage_screen/",
            "protocol": "4 quadrants x draws 20/21, models trained with hidden components removed",
            "c0_ordered_dots_mean_dti": 0.14086084085915884,
            "c1_geodesic_dots_mean_dti": 0.14479018210246675,
            "historical_d28_same_protocol": 0.09832,
            "note": "proxy only; the artifact itself trains on the full catalogue so its own proxy score would be contaminated and is not computed",
        },
        "artifact": {
            "file": name,
            "bytes": out_path.stat().st_size,
            "sha256": sha256_file(out_path),
            "content_id": cid,
            "positive_pixels": n_dots,
            "note": note,
            "zip": zpath.name,
        },
        "inputs": {
            "labels.tif": {"sha256": sha256_file(labels_path), "bytes": labels_path.stat().st_size},
            "sample_submission.tif": {"sha256": sha256_file(template), "bytes": template.stat().st_size},
        },
        "git": git_state(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "provenance_warning": (
            "Owner-mirror inputs are byte-verified but not organizer-authenticated; this is a research candidate, "
            "not an official score, and no weekly slot is approved by this repository."
        ),
    }
    # Diagnostics that do not require hidden truth.
    near_vis = distance_transform_edt(~ctx.labels) <= 3
    record["artifact"]["on_catalogue_pixels"] = int((emitted & ctx.labels).sum())
    record["artifact"]["hug_share_within_300m_of_catalogue"] = float((emitted & near_vis).sum() / max(n_dots, 1))
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {out_path}")
    print(f"wrote {zpath}")
    print(f"wrote {args.record}")
    print(f"note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
