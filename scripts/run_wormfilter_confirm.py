#!/usr/bin/env python3
"""H52-F confirmation: the worm-survival *feature* block on fresh draws 36/37.

Protocol, arms and gates are frozen in ``knowledge/39_preregistered_wormfilter_confirm_2026-10-03.md``
BEFORE this script runs. The runner records that file's SHA-256, the input/cache/module hashes and the
git state into ``evidence/wormfilter_confirm/design.json``, refuses to overwrite existing evidence,
requires a clean committed worktree, refuses to run on a draw below the ledger's ``next_free_draw``,
and never contacts DrivenData.

    python3 scripts/run_wormfilter_confirm.py

Three arms on each of the 8 cells (4 folds x draws 36/37): the two frozen controls ``C0_base`` and
``C1_geodesic_dots`` on the 81-column control matrix, and ``W5_surv_features`` — the same matrix plus
the eight label-free ``WF_*`` columns from ``src/gemsdoe/wormfilter.py`` — with the ``C0`` emission.
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
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import Cell, HGB_PARAMS, load_context  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import dot_thin, score_ordered_dots  # noqa: E402
from gemsdoe.wormfilter import WF_NAMES  # noqa: E402

PREREG = ROOT / "knowledge" / "39_preregistered_wormfilter_confirm_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "wormfilter_confirm"
LEDGER = ROOT / "registry" / "draw_ledger.json"
FIELDS = ("wormfilter_fields.npy", "wormfilter_fields.json")
FOLDS = (0, 1, 2, 3)
FOLD_NAMES = ("NW", "NE", "SW", "SE")
DRAWS = (36, 37)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
HOLDOUT_BEST = 0.14479018210246675
PRIMARY_ARM = "W5_surv_features"
ARMS = ("C0_base", "C1_geodesic_dots", "W5_surv_features")
GATES = dict(
    primary_arm=PRIMARY_ARM,
    mean_gain=0.005,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    budget_ratio_band=(0.75, 1.25),
    sgmc_min_mean_gain=0.000,
    sgmc_min_positive_folds=3,
    control_level_band=(0.1300, 0.1550),
    min_split_cells=3,
    max_single_column_split_share=0.50,
    holdout_best=HOLDOUT_BEST,
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
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as source:
        sgmc = source.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    truth = sgmc & ~labels & ~near
    return truth, dict(sgmc_positive=int(sgmc.sum()), off_catalogue=int(truth.sum()),
                       on_catalogue=int((sgmc & labels).sum()), within_300m=int((sgmc & ~labels & near).sum()))


def split_accounting(model, names: list[str]) -> dict[str, int]:
    used: dict[str, int] = {}
    for stage in getattr(model, "_predictors", []):
        for predictor in stage:
            for f in predictor.nodes["feature_idx"]:
                used[names[int(f)]] = used.get(names[int(f)], 0) + 1
    return used


def run_cells(ctx, vectors: np.ndarray, sink, sgmc_truth: np.ndarray) -> list[dict]:
    rows: list[dict] = []
    for fold in FOLDS:
        for draw in DRAWS:
            t0 = time.time()
            cell = Cell(ctx, fold, draw, extras=True, h27=True)
            base_n = cell.Xtr.shape[1]
            if len(ctx.all_names) != base_n:
                raise SystemExit(f"control matrix has {base_n} columns but {len(ctx.all_names)} names")
            names = list(ctx.all_names) + list(WF_NAMES)
            k = int(round(KFRAC * cell.dom_c.sum()))
            sl = cell.sl

            # Memory discipline on the 3 GB sandbox: fit the two controls on the base matrix first, then
            # build the extended matrices and release cell.Xtr/cell.Xq before the third fit.
            emissions: dict[str, np.ndarray] = {}
            timing: dict[str, dict] = {}
            aucs: dict[str, float] = {}
            diag: dict[str, dict] = {}
            for arm in ("C0_base", "C1_geodesic_dots"):
                model = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
                t_fit = time.time()
                model.fit(cell.Xtr, cell.y)
                fit_s = time.time() - t_fit
                t_pred = time.time()
                p = model.predict_proba(cell.Xq)[:, 1].astype(np.float32)
                timing[arm] = dict(fit_s=fit_s, predict_s=time.time() - t_pred, n_features=base_n)
                aucs[arm] = cell.auc(np.nan_to_num(p, nan=0.0))
                score, cand = cell.candidates(p, k)
                del p, model
                emissions[arm] = (score_ordered_dots(score, cand, MIN_DIST_PX) if arm == "C0_base"
                                  else dot_thin(cand, MIN_DIST_PX))
                del score, cand

            Xtr_w = np.concatenate([cell.Xtr] + [vectors[i][cell.train_idx][:, None] for i in range(len(WF_NAMES))], axis=1)
            Xq_w = np.concatenate([cell.Xq] + [vectors[i][cell.q][:, None] for i in range(len(WF_NAMES))], axis=1)
            del cell.Xtr, cell.Xq
            arm = PRIMARY_ARM
            model = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
            t_fit = time.time()
            model.fit(Xtr_w, cell.y)
            fit_s = time.time() - t_fit
            t_pred = time.time()
            p = model.predict_proba(Xq_w)[:, 1].astype(np.float32)
            timing[arm] = dict(fit_s=fit_s, predict_s=time.time() - t_pred, n_features=int(Xtr_w.shape[1]))
            aucs[arm] = cell.auc(np.nan_to_num(p, nan=0.0))
            used = split_accounting(model, names)
            wf = {n: c for n, c in used.items() if n in WF_NAMES}
            total = max(sum(used.values()), 1)
            diag[arm] = dict(
                wf_splits=int(sum(wf.values())), total_splits=total,
                wf_split_share=float(sum(wf.values()) / total),
                max_single_column_share=float(max(used.values()) / total) if used else 0.0,
                max_single_column=max(used, key=used.get) if used else None,
                wf_columns_used=sorted(wf), features_used=len(used),
                top_features=sorted(used.items(), key=lambda kv: -kv[1])[:5])
            score, cand = cell.candidates(p, k)
            del p, Xq_w
            emissions[arm] = score_ordered_dots(score, cand, MIN_DIST_PX)
            del score, cand, model
            del Xtr_w
            for arm in ARMS:
                emitted = emissions[arm]
                result = cell.evaluate(emitted)
                sg = dti_binary(emitted, sgmc_truth[sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                row = dict(fold=fold, fold_name=FOLD_NAMES[fold], draw=draw, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]), k=k,
                           identical_to_c0=bool(np.array_equal(emitted, emissions["C0_base"])),
                           auc=aucs[arm], **timing[arm])
                if arm == PRIMARY_ARM:
                    row["feature_diag"] = diag[arm]
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            brief = " ".join(f"{a.split('_')[0]}={next(r['dti'] for r in rows if r['fold'] == fold and r['draw'] == draw and r['arm'] == a):.4f}"
                             for a in ARMS)
            print(f"fold={FOLD_NAMES[fold]} draw={draw} {brief} "
                  f"wf_splits={diag[PRIMARY_ARM]['wf_splits']} ({time.time() - t0:.0f}s)", flush=True)
    return rows


def gate_summary(rows: list[dict]) -> dict:
    def mean(field: str, arm: str, fold: int | None = None) -> float:
        vals = [r[field] for r in rows if r["arm"] == arm and (fold is None or r["fold"] == fold)]
        return float(np.mean(vals)) if vals else float("nan")

    control_means = {fold: max(mean("dti", "C0_base", fold), mean("dti", "C1_geodesic_dots", fold)) for fold in FOLDS}
    gains = [mean("dti", PRIMARY_ARM, fold) - control_means[fold] for fold in FOLDS]
    sgmc_gains = [mean("sgmc_dti", PRIMARY_ARM, fold)
                  - max(mean("sgmc_dti", "C0_base", fold), mean("sgmc_dti", "C1_geodesic_dots", fold))
                  for fold in FOLDS]
    c0_mean, c1_mean, primary_mean = mean("dti", "C0_base"), mean("dti", "C1_geodesic_dots"), mean("dti", PRIMARY_ARM)

    budget_ratios = []
    for fold in FOLDS:
        for draw in DRAWS:
            arm_rows = [r for r in rows if r["arm"] == PRIMARY_ARM and r["fold"] == fold and r["draw"] == draw]
            c0_rows = [r for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] == draw]
            if arm_rows and c0_rows:
                budget_ratios.append(arm_rows[0]["emitted"] / max(c0_rows[0]["emitted"], 1))
    lo, hi = GATES["budget_ratio_band"]
    budget_ok = bool(budget_ratios and all(lo <= ratio <= hi for ratio in budget_ratios))

    feature_rows = [r for r in rows if r["arm"] == PRIMARY_ARM]
    split_cells = int(sum(1 for r in feature_rows if r["feature_diag"]["wf_splits"] > 0))
    distinct_cells = int(sum(1 for r in feature_rows if not r["identical_to_c0"]))
    max_share = float(max(r["feature_diag"]["max_single_column_share"] for r in feature_rows))
    band_lo, band_hi = GATES["control_level_band"]

    gates = dict(
        mean_gain=float(np.mean(gains)), fold_gains=gains, worst_fold=float(np.min(gains)),
        positive_folds=int(sum(g > 0 for g in gains)), budget_ok=budget_ok,
        budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
        budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        c0_mean=c0_mean, c1_mean=c1_mean, primary_mean_dti=primary_mean,
        bar_from_stored=HOLDOUT_BEST,
        sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_fold_gains=sgmc_gains,
        sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
        cells_present=bool(len(rows) == len(FOLDS) * len(DRAWS) * len(ARMS)),
        all_finite=bool(all(np.isfinite(r["dti"]) for r in rows)),
        control_level_in_band=bool(band_lo <= c0_mean <= band_hi and band_lo <= c1_mean <= band_hi),
        wf_split_cells=split_cells, distinct_from_c0_cells=distinct_cells,
        max_single_column_split_share=max_share,
    )
    g1 = bool(gates["mean_gain"] >= GATES["mean_gain"] and gates["positive_folds"] >= GATES["min_positive_folds"]
              and gates["worst_fold"] >= GATES["max_fold_loss"] and budget_ok)
    g2 = bool(primary_mean > GATES["holdout_best"])
    g3 = bool(gates["sgmc_mean_gain"] >= GATES["sgmc_min_mean_gain"]
              and gates["sgmc_positive_folds"] >= GATES["sgmc_min_positive_folds"])
    g4 = bool(gates["cells_present"] and gates["all_finite"] and gates["control_level_in_band"])
    g5 = bool(distinct_cells >= 1 and split_cells >= GATES["min_split_cells"])
    g6 = bool(max_share <= GATES["max_single_column_split_share"])
    if not g4:
        verdict = ("NOT COMPARABLE: cells missing/non-finite or the in-run control level is outside the "
                   "historical band; no verdict is issued.")
    elif not g5:
        verdict = "FAIL-INERT: the WF block changed nothing; no promotion."
    elif not g6:
        verdict = "LEAK-GUARD FAIL (G6): one column dominates the splits; no artifact may be packaged."
    elif g1 and g2 and g3:
        verdict = "SLOT-ELIGIBLE by the frozen rule: a cross-fitted WF artifact may be built for owner review."
    elif g1 and g2 and not g3:
        verdict = "PRIMARY PASS, SECONDARY-PROXY CONFLICT: no promotion (the H41 outcome)."
    else:
        verdict = "NO PROMOTION: the worm-survival feature block does not clear the frozen gates on fresh draws."
    return dict(arms={arm: mean("dti", arm) for arm in ARMS}, controls=control_means, gates=gates,
                gate_checks=dict(G1=g1, G2=g2, G3=g3, G4=g4, G5=g5, G6=g6), verdict=verdict)


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

    ledger = json.loads(LEDGER.read_text())
    next_free = int(ledger.get("next_free_draw", 0))
    if min(DRAWS) < next_free:
        raise SystemExit(f"refusing to run on draw {min(DRAWS)}: the ledger's next_free_draw is {next_free}")

    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    inputs = [data / "labels.tif", data / "external" / "derived_sgmc_faults_100m_u8.tif"]
    missing = [str(p) for p in inputs if not p.is_file()]
    missing += [str(work / name) for name in ("static_ABCD.npy", "addons.npy", *FIELDS) if not (work / name).is_file()]
    if missing:
        raise SystemExit(f"missing inputs/caches: {missing}")

    ctx = load_context(work)
    vectors = np.load(work / FIELDS[0], mmap_mode="r")
    field_meta = json.loads((work / FIELDS[1]).read_text())
    if vectors.shape != (len(WF_NAMES), ctx.fi.size):
        raise SystemExit("cached worm fields do not match the footprint vector")
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)

    design = dict(
        stage="wormfilter_confirm", experiment="H52-F worm-survival feature block, fresh-draw confirmation",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        selection_disclosure="the arm was selected from the H52 screen on draws 20/21; this stage is the "
                             "unbiased test on fresh draws and only W5_surv_features can promote",
        folds=[FOLD_NAMES[f] for f in FOLDS], draws=list(DRAWS), arms=list(ARMS), primary_arm=PRIMARY_ARM,
        gates=GATES, ledger_next_free_draw=next_free,
        worm_fields=dict(config=field_meta["config"], ladder=field_meta["ladder"],
                         cache_sha256={name: sha256_file(work / name) for name in FIELDS}),
        sgmc=sgmc_stats,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         scikit_learn=package_version("scikit-learn"), scipy=package_version("scipy"),
                         rasterio=package_version("rasterio"), platform=platform.platform()),
        modules={p: sha256_file(ROOT / p) for p in ("src/gemsdoe/wormfilter.py", "src/gemsdoe/experiment.py",
                                                    "src/gemsdoe/thinning.py", "src/gemsdoe/metric.py",
                                                    "scripts/run_wormfilter_confirm.py")},
        git=state, drivendata_contacted=False, started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    design_path.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")
    print(f"design frozen: {design_path.relative_to(ROOT)} (prereg sha256 {design['preregistration']['sha256'][:12]}…)")

    t0 = time.time()
    with cells_path.open("w") as sink:
        rows = run_cells(ctx, np.asarray(vectors), sink, sgmc_truth)
    summary = gate_summary(rows)
    summary["elapsed_s"] = round(time.time() - t0, 1)
    summary["cells"] = len(rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["gate_checks"], sort_keys=True))
    print(f"arms: {json.dumps({k: round(v, 5) for k, v in summary['arms'].items()})}")
    print(f"mean gain {summary['gates']['mean_gain']:+.6f} | primary mean {summary['gates']['primary_mean_dti']:.5f}")
    print(summary["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
