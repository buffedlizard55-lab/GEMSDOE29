#!/usr/bin/env python3
"""H34 paired screen: metric-native coverage emission versus the frozen Poisson-disk control.

Design, arms and gates are frozen in ``knowledge/08_preregistered_h34_coverage_emission_2026-10-03.md``
before this script is run on competition data. Nothing here contacts DrivenData; all inputs are the
hash-pinned owner mirrors restored by ``scripts/restore_h31_data.py``.

    GEMS_DATA_DIR=/tmp/gemsdoe29-data GEMS_WORK_DIR=/tmp/gemsdoe29-work \
        python3 scripts/run_h34_coverage_screen.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.coverage import greedy_coverage  # noqa: E402
from gemsdoe.experiment import Cell, load_context  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import dot_thin, ridge_nms, score_ordered_dots  # noqa: E402

FOLDS = ("NW", "NE", "SW", "SE")
DRAWS = (20, 21)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
RADIUS_PX = 3.0
MIN_SEP_PX = 2.0
GAIN_FLOOR = 0.02
PRIMARY = "C2_coverage_rule"
CONTROLS = ("C0_ordered_dots", "C1_geodesic_dots")
ARMS = ("C0_ordered_dots", "C1_geodesic_dots", "C2_coverage_rule", "C3_coverage_binary")
GATES = dict(
    min_mean_gain=0.001,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    max_budget_ratio=3.0,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def git_revision() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unavailable"

    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"), dirty=bool(run("status", "--porcelain")))


def sgmc_class(data: Path, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """State-geologic-map faults that are neither catalogue pixels nor within 300 m of one."""
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    truth = sg & ~labels & ~near
    return truth, dict(
        sgmc_positive=int(sg.sum()),
        off_catalogue=int(truth.sum()),
        on_catalogue=int((sg & labels).sum()),
        within_300m=int((sg & ~labels & near).sum()),
    )


def emit_arms(cell: Cell, probabilities: np.ndarray, k: int) -> tuple[dict[str, np.ndarray], dict]:
    """Build the four frozen arms on one fitted score field (all crops of the test quadrant)."""
    score_crop, candidates = cell.candidates(probabilities, k)
    c0 = score_ordered_dots(score_crop, candidates, MIN_DIST_PX)
    c1 = dot_thin(candidates, MIN_DIST_PX)
    ridge = ridge_nms(score_crop, cell.dom_c, 1.0)
    valid = cell.dom_c & ~cell.known_c
    prior = np.where(ridge & valid, score_crop, 0.0).astype(np.float32)
    n0 = int(c0.sum())
    budgets = tuple(sorted({int(round(n0 * f)) for f in (1.0, 1.5, 2.0, 3.0)} - {0}))
    cov = greedy_coverage(prior, valid, budgets=budgets, radius_px=RADIUS_PX, min_sep_px=MIN_SEP_PX, gain_floor=GAIN_FLOOR)
    best_budget = max(cov.levels, key=lambda row: row["dti_hat"])["n"] if cov.levels else n0
    chosen = min(budgets, key=lambda b: abs(b - best_budget)) if budgets else n0
    c2 = cov.emissions[chosen]
    prior_bin = (prior > 0).astype(np.float32)
    cov_bin = greedy_coverage(
        prior_bin, valid, budgets=(int(c2.sum()),) if c2.sum() else (n0,), radius_px=RADIUS_PX, min_sep_px=MIN_SEP_PX,
        gain_floor=GAIN_FLOOR,
    )
    c3 = cov_bin.emissions[int(c2.sum())] if int(c2.sum()) in cov_bin.emissions else next(iter(cov_bin.emissions.values()))
    diagnostics = dict(
        k=int(k),
        n_control_candidates=int(candidates.sum()),
        n0=int(n0),
        budgets=list(budgets),
        chosen_budget=int(chosen),
        dti_hat_curve=[{k2: float(v2) if isinstance(v2, float) else v2 for k2, v2 in row.items()} for row in cov.levels],
        coverage_diag=cov.diagnostics,
    )
    return {ARMS[0]: c0, ARMS[1]: c1, ARMS[2]: c2, ARMS[3]: c3}, diagnostics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "h34_coverage_screen"))
    ap.add_argument("--folds", default="0,1,2,3", help="comma-separated fold ids (default all four)")
    ap.add_argument("--draws", default="20,21", help="comma-separated draw seeds (frozen default 20,21)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cells_path = out / "cells.jsonl"
    design_path = out / "design.json"
    if design_path.exists() or cells_path.exists():
        raise SystemExit(f"refusing to overwrite existing evidence in {out}")

    data, work = data_dir(), work_dir()
    required = ["labels.tif", "sample_submission.tif", "training_features.tif", "external/derived_sgmc_faults_100m_u8.tif"]
    missing = [r for r in required if not (data / r).is_file()]
    if missing:
        raise SystemExit(f"missing restored owner-mirror inputs: {missing}; run scripts/restore_h31_data.py --group all")
    folds = [int(x) for x in args.folds.split(",")]
    draws = [int(x) for x in args.draws.split(",")]

    design = dict(
        experiment="H34 metric-native coverage emission screen",
        preregistration="knowledge/08_preregistered_h34_coverage_emission_2026-10-03.md",
        protocol="paired, same fitted model and score field per (fold, draw); four fresh/registered arms",
        folds=[FOLDS[f] for f in folds],
        draws=draws,
        draw_seed_inventory={"used_before": "0-13 (0-9 on main, 10-13 frozen H31)", "this_screen": draws},
        arms=list(ARMS),
        primary=PRIMARY,
        controls=list(CONTROLS),
        gates=GATES,
        constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX, radius_px=RADIUS_PX, min_sep_px=MIN_SEP_PX, gain_floor=GAIN_FLOOR),
        git=git_revision(),
        environment=dict(python=platform.python_version(), numpy=np.__version__, packages={n: package_version(n) for n in ("rasterio", "scikit-learn", "scipy", "numpy")}),
        inputs={r: dict(sha256=sha256_file(data / r), bytes=(data / r).stat().st_size) for r in required},
    )
    design_path.write_text(json.dumps(design, indent=2) + "\n")

    ctx = load_context(work)
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)
    print(f"H34 screen: folds {folds}, draws {draws}; SGMC off-catalogue truth {sgmc_stats['off_catalogue']:,} px")
    rows: list[dict] = []
    t_start = time.time()
    with cells_path.open("w", encoding="utf-8") as sink:
        for fold in folds:
            for seed in draws:
                t0 = time.time()
                cell = Cell(ctx, fold, seed, extras=True, h27=True)
                cols = list(range(cell.Xtr.shape[1]))
                probabilities, timing = cell.fit_predict(cols, seed=seed)
                k = int(round(KFRAC * cell.dom_c.sum()))
                emissions, diagnostics = emit_arms(cell, probabilities, k)
                for arm in ARMS:
                    emitted = emissions[arm]
                    result = cell.evaluate(emitted)
                    sl = cell.sl
                    sg = dti_binary(emitted, sgmc_truth[sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                    row = dict(
                        fold=fold,
                        fold_name=FOLDS[fold],
                        draw=seed,
                        arm=arm,
                        **result,
                        sgmc_dti=float(sg["dti"]),
                        sgmc_coverage=float(sg["coverage"]),
                        sgmc_n_truth=int(sg["n_truth"]),
                        fit_s=float(timing["fit_s"]),
                        predict_s=float(timing["predict_s"]),
                    )
                    if arm == PRIMARY:
                        row["emission_diagnostics"] = diagnostics
                    rows.append(row)
                    sink.write(json.dumps(row) + "\n")
                    sink.flush()
                print(
                    f"fold={FOLDS[fold]} draw={seed} "
                    + " ".join(f"{a.split('_')[0]}={next(r for r in rows if r['fold'] == fold and r['draw'] == seed and r['arm'] == a)['dti']:.4f}" for a in ARMS)
                    + f"  ({time.time() - t0:.0f}s)",
                    flush=True,
                )

    # --- gate -------------------------------------------------------------------------------------
    def mean_dti(arm: str, fold: int) -> float:
        vals = [r["dti"] for r in rows if r["fold"] == fold and r["arm"] == arm]
        return float(np.mean(vals)) if vals else float("nan")

    gains, budget_ratios, sgmc_gains = [], [], []
    for fold in folds:
        control = max(mean_dti(a, fold) for a in CONTROLS)
        gains.append(mean_dti(PRIMARY, fold) - control)
        n_primary = np.mean([r["emitted"] for r in rows if r["fold"] == fold and r["arm"] == PRIMARY])
        n_control = np.mean([r["emitted"] for r in rows if r["fold"] == fold and r["arm"] == CONTROLS[0]])
        budget_ratios.append(float(n_primary / max(n_control, 1)))
        sgmc_gains.append(
            float(np.mean([r["sgmc_dti"] for r in rows if r["fold"] == fold and r["arm"] == PRIMARY]))
            - max(float(np.mean([r["sgmc_dti"] for r in rows if r["fold"] == fold and r["arm"] == a])) for a in CONTROLS)
        )
    gates = dict(
        mean_gain=float(np.mean(gains)),
        positive_folds=int(sum(1 for g in gains if g > 0)),
        worst_fold=float(np.min(gains)),
        max_budget_ratio=float(np.max(budget_ratios)),
        sgmc_mean_gain=float(np.mean(sgmc_gains)),
        sgmc_positive_folds=int(sum(1 for g in sgmc_gains if g > 0)),
        all_cells_present=bool(len(rows) == len(folds) * len(draws) * len(ARMS)),
        all_finite=bool(all(np.isfinite(r["dti"]) for r in rows)),
    )
    g1 = gates["mean_gain"] > GATES["min_mean_gain"]
    g2 = gates["positive_folds"] >= GATES["min_positive_folds"]
    g3 = gates["worst_fold"] > GATES["max_fold_loss"]
    g4 = gates["max_budget_ratio"] <= GATES["max_budget_ratio"]
    g5 = gates["all_cells_present"] and gates["all_finite"]
    summary = dict(
        experiment="H34 metric-native coverage emission screen",
        elapsed_s=time.time() - t_start,
        arms={a: float(np.mean([r["dti"] for r in rows if r["arm"] == a])) for a in ARMS},
        sgmc_arms={a: float(np.mean([r["sgmc_dti"] for r in rows if r["arm"] == a])) for a in ARMS},
        paired_gains_vs_best_control=gains,
        sgmc_paired_gains=sgmc_gains,
        budget_ratios=budget_ratios,
        gates=gates,
        gate_checks=dict(mean_gain=g1, positive_folds=g2, worst_fold=g3, budget=g4, cells=g5),
        sgmc_stats=sgmc_stats,
        pass_fail="PASS" if all((g1, g2, g3, g4, g5)) else "FAIL",
        interpretation=(
            "Proxy outcome only: exact masked DTI on hidden catalogue components plus a secondary "
            "state-geologic-map off-catalogue class. Neither is the organizer's hidden expert label set "
            "and neither is a competition score."
        ),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("arms", "sgmc_arms", "paired_gains_vs_best_control", "budget_ratios", "gates", "pass_fail")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
