#!/usr/bin/env python3
"""Design-stage audit of the H53 fabric variants **on spent draws only** (no gate, no verdict).

Purpose: choose the one frozen H53 formulation *before* the screen, with the choice measured rather
than asserted. Three variants are declared up front (raw detrended elevation, high-pass at 3 km,
high-pass at 6 km); for each, the four candidate columns are measured on the two spent H34 draws
(20/21) of fold NW only, against that draw's own hide-and-recover truth, on the eroded domain:

* distribution: nonzero fraction, mean, and the 1/50/99th percentiles;
* discrimination: AUC of each single column against the draw's hidden test components (positives)
  versus the domain's non-catalogue pixels (150 k sampled negatives) -- a *design* statistic, never a
  gate;
* catalogue-adjacency: share of the column's top decile within 300 m of the visible catalogue, so a
  field that merely re-expresses the catalogue can be rejected before the screen;
* correlation with the existing DEM-family columns (`det_elev`, `det_elev_slope`, `B_crest`,
  `B_trough`, `L_step_max`) on the same draw, so a redundant field can be rejected too.

The selection rule is frozen here as well, before the numbers are read: **pick the variant whose
primary column (`H53_PERSIST`) has the best off-catalogue AUC in the NW/spent-draw audit, provided its
top decile is not more catalogue-hugging than the base column `det_elev_slope`**; ties break to the
smaller high-pass scale. The audit writes ``evidence/h53_design_audit.json`` and reads no labels other
than the spent draws' own hidden components. Draws 36/37 -- the screen draws -- are never touched.

    GEMS_DATA_DIR=$PWD/data python scripts/audit_h53_fields.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import DOMAIN_ERODE  # noqa: E402
from gemsdoe.h53 import H53_NAMES, H53Config, build_h53_fields  # noqa: E402
from gemsdoe.holdout import Holdout  # noqa: E402
from gemsdoe.paths import work_dir  # noqa: E402

OUT = ROOT / "evidence" / "h53_design_audit.json"
VARIANTS = (
    ("raw", dict(highpass_sigma_px=0.0)),
    ("hp30", dict(highpass_sigma_px=30.0)),
    ("hp60", dict(highpass_sigma_px=60.0)),
)
FOLD, DRAW = 0, 20  # NW, spent draw (registry/draw_ledger.json)
CORRELATES = ("det_elev", "det_elev_slope", "B_crest", "B_trough", "L_step_max")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantiles(row: np.ndarray) -> dict:
    v = np.asarray(row, np.float64)
    return dict(mean=float(v.mean()), p01=float(np.percentile(v, 1)), p50=float(np.percentile(v, 50)),
                p99=float(np.percentile(v, 99)), nonzero_fraction=float(np.mean(v > 0)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    work = work_dir()
    foot = np.load(work / "bands" / "_footprint.npy")
    labels = np.load(work / "bands" / "_labels.npy")
    fi = np.flatnonzero(foot.ravel())
    holdout = Holdout(foot, labels, 0.20)
    draw = holdout.draw(FOLD, DRAW)
    quadrant = draw.quadrant
    domain = binary_erosion(quadrant, iterations=DOMAIN_ERODE)
    truth = draw.hidden_test & domain
    known = draw.visible
    near_visible = distance_transform_edt(~known) <= 3
    neg_pool = np.flatnonzero((domain & ~labels).ravel())
    neg = np.random.default_rng(5).choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
    pos = np.flatnonzero(truth.ravel())
    print(f"design draw: fold={holdout.__class__.__name__} NW draw={DRAW} positives={pos.size} negatives={neg.size}")

    results: dict[str, dict] = {}
    for label, overrides in VARIANTS:
        config = H53Config(**overrides)
        t0 = time.time()
        vectors, _grids, diag = build_h53_fields(work / "bands", foot, fi, config=config)
        vectors = np.asarray(vectors, np.float64)
        per_column = {}
        top_decile_hug = {}
        for i, name in enumerate(H53_NAMES):
            full = np.zeros(foot.size, np.float32)
            full[fi] = vectors[i]
            row = full.ravel()
            auc = float(roc_auc_score(np.concatenate([np.ones(pos.size), np.zeros(neg.size)]),
                                      np.concatenate([row[pos], row[neg]]))) if pos.size and neg.size else float("nan")
            off_pos = pos[~near_visible.ravel()[pos]]
            off_auc = float(roc_auc_score(np.concatenate([np.ones(off_pos.size), np.zeros(neg.size)]),
                                          np.concatenate([row[off_pos], row[neg]]))) if off_pos.size and neg.size else float("nan")
            thr = float(np.quantile(row[domain.ravel()], 0.90))
            top = domain.ravel() & (row >= thr)
            top_decile_hug[name] = float(np.mean(near_visible.ravel()[top])) if top.any() else float("nan")
            per_column[name] = dict(quantiles=quantiles(row[fi]), auc=auc, off_catalogue_auc=off_auc,
                                    off_catalogue_positives=int(off_pos.size))
        corr = {}
        static = np.load(work / "static_ABCD.npy", mmap_mode="r")
        names = json.loads((work / "static_ABCD.npy.names.json").read_text())
        dom_vec = domain.ravel()[fi]
        for i, name in enumerate(H53_NAMES):
            row = vectors[i]
            corr[name] = {}
            for base in CORRELATES:
                j = names.index(base)
                b = np.asarray(static[j], np.float32)
                m = dom_vec & np.isfinite(b) & np.isfinite(row)
                if m.sum() > 10:
                    corr[name][base] = float(np.corrcoef(row[m], np.asarray(b, np.float64)[m])[0, 1])
        results[label] = dict(highpass_sigma_px=float(config.highpass_sigma_px), elapsed_s=round(time.time() - t0, 1),
                              per_column=per_column, top_decile_catalogue_hug=top_decile_hug,
                              correlation=corr, diagnostics_nonzero=diag["nonzero_fraction"])
        print(f"variant {label:5s} ({time.time() - t0:5.1f}s) " + " ".join(
            f"{n.split('_', 1)[1]}={per_column[n]['off_catalogue_auc']:.4f}" for n in H53_NAMES), flush=True)

    base_hug: dict[str, float] = {}
    base_auc: dict[str, float] = {}
    base_off_auc: dict[str, float] = {}
    static = np.load(work / "static_ABCD.npy", mmap_mode="r")
    names = json.loads((work / "static_ABCD.npy.names.json").read_text())
    dom_vec = domain.ravel()[fi]
    pos_vec = pos  # footprint-vector indices of the draw's hidden test components
    off_pos_vec = pos_vec[~near_visible.ravel()[fi][pos_vec]]
    for base in CORRELATES:
        b = np.nan_to_num(np.asarray(static[names.index(base)], np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        thr = float(np.quantile(b[dom_vec], 0.90))
        top = dom_vec & (b >= thr)
        base_hug[base] = float(np.mean(near_visible.ravel()[fi][top])) if top.any() else float("nan")
        base_auc[base] = float(roc_auc_score(np.concatenate([np.ones(pos_vec.size), np.zeros(neg.size)]),
                                             np.concatenate([b[pos_vec], b[neg]])))
        base_off_auc[base] = float(roc_auc_score(np.concatenate([np.ones(off_pos_vec.size), np.zeros(neg.size)]),
                                                 np.concatenate([b[off_pos_vec], b[neg]])))
    ranked = sorted(results, key=lambda v: (-results[v]["per_column"]["H53_PERSIST"]["off_catalogue_auc"], v))
    chosen = next((v for v in ranked
                   if results[v]["top_decile_catalogue_hug"]["H53_PERSIST"] <= base_hug["det_elev_slope"]), ranked[0])
    payload = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        purpose="design-stage variant selection for the H53 screen; spent draw only, no gate, no verdict",
        design_draw=dict(fold="NW", fold_index=FOLD, draw=DRAW, positives=int(pos.size), negatives=int(neg.size),
                         note="spent draw (registry/draw_ledger.json); draws 36/37 are untouched"),
        selection_rule=("best H53_PERSIST off-catalogue AUC among the three declared variants, provided its top "
                        "decile is not more catalogue-hugging than det_elev_slope's top decile; ties -> smaller high-pass"),
        variants=results, chosen_variant=chosen, chosen_highpass_sigma_px=float(H53Config(**dict(VARIANTS)[chosen]).highpass_sigma_px),
        base_top_decile_catalogue_hug=base_hug,
        base_single_column_auc=base_auc, base_single_column_off_catalogue_auc=base_off_auc,
        environment=dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform()),
        inputs=dict(elev_band="12_det_elev.npy", elev_sha256=sha256_file(work / "bands" / "12_det_elev.npy"),
                    module_sha256=sha256_file(ROOT / "src" / "gemsdoe" / "h53.py")),
        label_free_in_build=True,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"chosen variant: {chosen} (H53_PERSIST off-catalogue AUC "
          f"{results[chosen]['per_column']['H53_PERSIST']['off_catalogue_auc']:.4f}); wrote {args.out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
