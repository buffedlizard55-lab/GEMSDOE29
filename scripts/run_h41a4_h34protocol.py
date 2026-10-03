#!/usr/bin/env python3
"""H41-A4 re-score on the H34 C0 protocol: does the replicated H41 gain clear the recorded slot bar?

Protocol, gates and the reuse of the spent draws 20/21 are frozen in
``knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md`` BEFORE this script runs. The runner records
that file's SHA-256, the input/cache/module hashes and the git state into
``evidence/h41a4_h34protocol/design.json``, refuses to overwrite existing evidence, requires a clean
committed worktree, and never contacts DrivenData.

    python3 scripts/run_h41a4_h34protocol.py

Three arms on each of the 8 cells (4 folds x draws 20/21): the frozen H34 controls ``C0_base`` (ordered dots)
and ``C1_geodesic_dots``, which reproduce the numbers that define the bar, plus ``A4_h41_union``, the five
frozen H41 columns over the same control matrix and the same emission as C0. The stored H34 C0/C1 values are
re-read from ``evidence/h34_coverage_screen/cells.jsonl`` and the reproduction is reported as gate G4.
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
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import Cell, HGB_PARAMS, load_context  # noqa: E402
from gemsdoe.h35 import _trace_grids  # noqa: E402
from gemsdoe.h41 import H41_NAMES, build_h41_fields, degenerate_fields, parse_centroids  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import dot_thin, score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "27_preregistered_h41a4_h34protocol_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "h41a4_h34protocol"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
QFAULTS_CSV = "external/gdr_qfaults_traces.csv"
FOLDS = (0, 1, 2, 3)
FOLD_NAMES = ("NW", "NE", "SW", "SE")
DRAWS = (20, 21)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
HOLDOUT_BEST = 0.14479018210246675  # recorded H34 C1_geodesic_dots mean (registry/status_feed.json)
ARMS = ("C0_base", "C1_geodesic_dots", "A4_h41_union")
GATES = dict(
    mean_gain=0.005,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    budget_ratio_band=(0.75, 1.25),
    sgmc_min_mean_gain=0.000,
    sgmc_min_positive_folds=3,
    min_nonzero_fraction=0.002,
    holdout_best=HOLDOUT_BEST,
    reproduction_tolerance=1e-6,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(f"git state unavailable ({exc}); the stage requires a clean committed tree") from exc

    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"),
                dirty_worktree=bool(run("status", "--porcelain")))


def sgmc_class(data: Path, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """State-geologic-map faults that are neither catalogue pixels nor within 300 m of one (H34 convention)."""
    from scipy.ndimage import binary_dilation
    import rasterio

    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as source:
        sgmc = source.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    truth = sgmc & ~labels & ~near
    return truth, dict(
        sgmc_positive=int(sgmc.sum()), off_catalogue=int(truth.sum()),
        on_catalogue=int((sgmc & labels).sum()), within_300m=int((sgmc & ~labels & near).sum()),
    )


def scarp_strike_grid(ctx) -> tuple[np.ndarray, np.ndarray]:
    """Grid-shaped (cos 2t, sin 2t) strike field of the H27 scarp composite (draw-independent)."""
    grid = np.zeros(ctx.foot.shape, np.float32)
    grid.ravel()[ctx.fi] = np.nan_to_num(ctx.h27_scarp, nan=0.0, posinf=0.0, neginf=0.0)
    cos2t, sin2t, _ = _trace_grids(grid)
    return cos2t, sin2t


def stored_h34_controls() -> dict[tuple[str, int, str], float]:
    """'the values that define the bar' as recorded in the H34 screen cells (dti only)."""
    out: dict[tuple[str, int, str], float] = {}
    if not H34_CELLS.is_file():
        return out
    for line in H34_CELLS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["arm"] in ("C0_ordered_dots", "C1_geodesic_dots"):
            out[(row["fold_name"], int(row["draw"]), row["arm"])] = float(row["dti"])
    return out


def emit_arms(cell: Cell, probabilities: np.ndarray, k: int) -> dict[str, np.ndarray]:
    """The two frozen H34 control emissions on one fitted score field."""
    score_crop, candidates = cell.candidates(probabilities, k)
    return {
        "C0_base": score_ordered_dots(score_crop, candidates, MIN_DIST_PX),
        "C1_geodesic_dots": dot_thin(candidates, MIN_DIST_PX),
    }


def run_cells(ctx, cfield, cos2t, sin2t, sink, sgmc_truth: np.ndarray, draws=DRAWS) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    guard_problems: list[str] = []
    for fold in FOLDS:
        for draw in draws:
            t0 = time.time()
            cell = Cell(ctx, fold, draw, extras=True, h27=True)
            base_n = cell.Xtr.shape[1]
            fields, diag = build_h41_fields(
                cfield, visible=cell.draw.visible, footprint=ctx.foot, footprint_idx=ctx.fi,
                scarp_vec=ctx.h27_scarp, cos2t=cos2t, sin2t=sin2t)
            problems = degenerate_fields(fields, min_nonzero_fraction=GATES["min_nonzero_fraction"])
            if problems:
                guard_problems.append(f"fold={FOLD_NAMES[fold]} draw={draw}: " + "; ".join(problems))
            # one extended matrix pair, replacing the base matrices in memory
            Xtr = np.concatenate([cell.Xtr] + [fields[i][cell.train_idx][:, None] for i in range(len(H41_NAMES))], axis=1)
            Xq = np.concatenate([cell.Xq] + [fields[i][cell.q][:, None] for i in range(len(H41_NAMES))], axis=1)
            del cell.Xtr, cell.Xq
            base_cols = list(range(base_n))
            all_cols = list(range(base_n + len(H41_NAMES)))
            k = int(round(KFRAC * cell.dom_c.sum()))

            plans = (("C0_base", base_cols), ("A4_h41_union", all_cols))
            emissions: dict[str, np.ndarray] = {}
            timing: dict[str, dict] = {}
            aucs: dict[str, float] = {}
            for arm, cols in plans:
                t_fit = time.time()
                model = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
                model.fit(np.ascontiguousarray(Xtr[:, cols]), cell.y)
                fit_s = time.time() - t_fit
                t_pred = time.time()
                p = model.predict_proba(np.ascontiguousarray(Xq[:, cols]))[:, 1].astype(np.float32)
                timing[arm] = dict(fit_s=fit_s, predict_s=time.time() - t_pred, n_features=len(cols))
                aucs[arm] = cell.auc(np.nan_to_num(p, nan=0.0))
                if arm == "C0_base":
                    emissions.update(emit_arms(cell, p, k))
                else:
                    score_crop, candidates = cell.candidates(p, k)
                    emissions["A4_h41_union"] = score_ordered_dots(score_crop, candidates, MIN_DIST_PX)
            del Xtr, Xq
            for arm in ARMS:
                emitted = emissions[arm]
                result = cell.evaluate(emitted)
                sg = dti_binary(emitted, sgmc_truth[cell.sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                row = dict(fold=fold, fold_name=FOLD_NAMES[fold], draw=draw, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]),
                           auc=aucs["C0_base" if arm == "C0_base" else "A4_h41_union"],
                           **timing["C0_base" if arm == "C0_base" else "A4_h41_union"])
                if arm == "C0_base":
                    row["h41_diag"] = diag
                    row["viability_guard"] = problems
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            brief = " ".join(f"{a.split('_')[0]}={next(r['dti'] for r in rows if r['fold'] == fold and r['draw'] == draw and r['arm'] == a):.4f}"
                             for a in ARMS)
            print(f"fold={FOLD_NAMES[fold]} draw={draw} {brief}  ({time.time() - t0:.0f}s)", flush=True)
    return rows, guard_problems


def gate_summary(rows: list[dict], stored: dict) -> dict:
    def mean(arm: str, fold: int | None = None, draw: int | None = None) -> float:
        vals = [r["dti"] for r in rows if r["arm"] == arm
                and (fold is None or r["fold"] == fold) and (draw is None or r["draw"] == draw)]
        return float(np.mean(vals)) if vals else float("nan")

    control_means = {fold: max(mean("C0_base", fold), mean("C1_geodesic_dots", fold)) for fold in FOLDS}
    gains = [mean("A4_h41_union", fold) - control_means[fold] for fold in FOLDS]

    def sgmc_mean(arm: str, fold: int) -> float:
        vals = [r["sgmc_dti"] for r in rows if r["arm"] == arm and r["fold"] == fold]
        return float(np.mean(vals)) if vals else float("nan")

    sgmc_gains = [sgmc_mean("A4_h41_union", fold)
                  - max(sgmc_mean("C0_base", fold), sgmc_mean("C1_geodesic_dots", fold)) for fold in FOLDS]
    budget_ok, budget_ratios = True, []
    for fold in FOLDS:
        for draw in DRAWS:
            arm_cells = [r for r in rows if r["arm"] == "A4_h41_union" and r["fold"] == fold and r["draw"] == draw]
            c0_cells = [r for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] == draw]
            if not arm_cells or not c0_cells:
                budget_ok = False
                continue
            ratio = arm_cells[0]["emitted"] / max(c0_cells[0]["emitted"], 1)
            budget_ratios.append(ratio)
            lo, hi = GATES["budget_ratio_band"]
            if not (lo <= ratio <= hi):
                budget_ok = False

    reproduction = []
    if stored:
        for row in rows:
            key = (row["fold_name"], row["draw"], "C0_ordered_dots" if row["arm"] == "C0_base" else "C1_geodesic_dots")
            if row["arm"] in ("C0_base", "C1_geodesic_dots") and key in stored:
                reproduction.append(dict(fold_name=row["fold_name"], draw=row["draw"], arm=row["arm"],
                                         rebuilt=float(row["dti"]), stored=float(stored[key]),
                                         delta=float(row["dti"]) - float(stored[key])))
    repro_max = max((abs(item["delta"]) for item in reproduction), default=float("nan"))

    mean_gain = float(np.mean(gains))
    a4_mean = mean("A4_h41_union")
    gates = dict(
        mean_gain=mean_gain, fold_gains=gains, worst_fold=float(np.min(gains)),
        positive_folds=int(sum(g > 0 for g in gains)), budget_ok=bool(budget_ok),
        budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
        budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        a4_mean_dti=a4_mean, bar_mean=max(control_means.values()),
        bar_from_stored=HOLDOUT_BEST,
        sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_fold_gains=sgmc_gains,
        sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
        cells_present=bool(len(rows) == len(FOLDS) * len(DRAWS) * len(ARMS)),
        all_finite=bool(all(np.isfinite(r["dti"]) for r in rows)),
        reproduction_max_abs_delta=repro_max, reproduction_cells=reproduction,
    )
    g1 = bool(mean_gain >= GATES["mean_gain"] and gates["positive_folds"] >= GATES["min_positive_folds"]
              and gates["worst_fold"] >= GATES["max_fold_loss"] and budget_ok)
    g2 = bool(a4_mean > GATES["holdout_best"])
    g3 = bool(gates["sgmc_mean_gain"] >= GATES["sgmc_min_mean_gain"]
              and gates["sgmc_positive_folds"] >= GATES["sgmc_min_positive_folds"])
    g4 = bool(gates["cells_present"] and gates["all_finite"] and np.isfinite(repro_max)
              and repro_max <= GATES["reproduction_tolerance"])
    if not g4:
        verdict = "NOT COMPARABLE: the frozen controls did not reproduce the stored H34 cells; no verdict is issued."
    elif g1 and g2 and g3:
        verdict = "SLOT-ELIGIBLE by the frozen rule: a candidate artifact may be built for owner review."
    elif g1 and g2 and not g3:
        verdict = "PRIMARY PASS, SECONDARY-PROXY CONFLICT: no promotion (the H41 outcome, measured against the real bar)."
    else:
        verdict = "NO PROMOTION: the H41 union arm does not clear the frozen gates on the bar protocol."
    return dict(arms={arm: mean(arm) for arm in ARMS}, controls=control_means, gates=gates,
                gate_checks=dict(G1=g1, G2=g2, G3=g3, G4=g4), verdict=verdict)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    out = args.out
    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    out.mkdir(parents=True, exist_ok=True)
    cells_path, design_path, summary_path = out / "cells.jsonl", out / "design.json", out / "summary.json"
    if design_path.exists() or cells_path.exists() or summary_path.exists():
        raise SystemExit(f"refusing to overwrite existing evidence in {out}")

    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    inputs = {rel: data / rel for rel in ("labels.tif", "sample_submission.tif", QFAULTS_CSV,
                                          "external/derived_sgmc_faults_100m_u8.tif")}
    missing = [str(p) for p in inputs.values() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing restored owner-mirror inputs: {missing}")
    for name in ("static_ABCD.npy", "addons.npy"):
        if not (work / name).is_file():
            raise SystemExit(f"missing feature cache {work / name}; run scripts/prepare_data.py and scripts/build_features.py first")

    stored = stored_h34_controls()
    if not stored:
        raise SystemExit("missing evidence/h34_coverage_screen/cells.jsonl; gate G4 cannot be evaluated")

    ctx = load_context(work)
    cfield = parse_centroids(inputs[QFAULTS_CSV], shape=ctx.foot.shape)
    cos2t, sin2t = scarp_strike_grid(ctx)
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)

    design = dict(
        stage="h41a4_h34protocol", experiment="H41-A4 re-score on the H34 C0 protocol (slot-bar comparison)",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        folds=[FOLD_NAMES[f] for f in FOLDS], draws=list(DRAWS), arms=list(ARMS), gates=GATES,
        constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX,
                       emit_C0="score_ordered_dots(score_crop, candidates, 2.4)",
                       emit_C1="dot_thin(candidates, 2.4)"),
        draw_seed_inventory={"used_before": "0-15, 20-25, 28-31 (registry/draw_ledger.json)",
                             "this_stage": list(DRAWS),
                             "note": "spent draws reused for a paired comparison against the bar they define; next_free_draw stays 32"},
        qfaults=dict(sha256=sha256_file(inputs[QFAULTS_CSV]),
                     **{k: v for k, v in cfield.diagnostics.items() if k != "file"}, support_scale=float(cfield.scale)),
        sgmc_stats=sgmc_stats,
        git=state,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         packages={n: package_version(n) for n in ("scipy", "scikit-learn", "rasterio")}),
        inputs={rel: dict(sha256=sha256_file(path), bytes=path.stat().st_size) for rel, path in inputs.items()},
        caches={name: dict(sha256=sha256_file(work / name)) for name in
                ("static_ABCD.npy", "static_ABCD.npy.names.json", "addons.npy", "addons.npy.names.json")},
        modules={f"gemsdoe/{m}": sha256_file(ROOT / "src" / "gemsdoe" / m)
                 for m in ("h41.py", "h35.py", "experiment.py", "thinning.py", "metric.py", "features.py")},
    )
    design_path.write_text(json.dumps(design, indent=2) + "\n")
    print(f"design recorded: {design_path} (git {state['revision'][:8]}, {len(DRAWS)} draws x {len(FOLDS)} folds x {len(ARMS)} arms)",
          flush=True)

    start = time.time()
    sink = cells_path.open("w")
    try:
        rows, guard_problems = run_cells(ctx, cfield, cos2t, sin2t, sink, sgmc_truth)
    finally:
        sink.close()
    summary = gate_summary(rows, stored)
    summary.update(
        stage="h41a4_h34protocol", elapsed_s=round(time.time() - start, 1), n_cells=len(rows), draws=list(DRAWS),
        folds=list(FOLD_NAMES), viability_guard=dict(min_nonzero_fraction=GATES["min_nonzero_fraction"],
                                                     problems=guard_problems, passed=not guard_problems),
        note=("Both proxies are local and neither is the organizer metric. Draws 20/21 are the spent draws that "
              "define the recorded bar; this stage re-measures on them and spends no fresh randomness."),
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("arms", "controls", "gate_checks", "verdict")}, indent=2))
    print(f"gates: {json.dumps(summary['gates']['mean_gain'])} mean gain, worst fold {summary['gates']['worst_fold']:+.7f}, "
          f"SGMC mean {summary['gates']['sgmc_mean_gain']:+.7f} ({summary['gates']['sgmc_positive_folds']}/4 folds), "
          f"reproduction max |delta| {summary['gates']['reproduction_max_abs_delta']:.3e}", flush=True)
    if guard_problems:
        print(f"VIABILITY GUARD FAILED ({len(guard_problems)} cells): " + "; ".join(guard_problems), flush=True)
    print(f"wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
