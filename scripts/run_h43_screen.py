#!/usr/bin/env python3
"""H43 screen: drainage-network organization (stream-power residual and knickpoint excess) vs frozen C0 control.

Protocol, arms, gates, draws and the degeneracy guard are frozen in
``knowledge/27_preregistered_h43_screen_2026-10-03.md`` BEFORE this script runs; the runner records that
file's SHA-256 plus source/input hashes into ``evidence/h43_screen/design_<stage>.json`` and refuses to
overwrite existing evidence. It requires a clean committed worktree and never contacts DrivenData; all
inputs are the hash-pinned owner mirrors restored under ``GEMS_DATA_DIR``.

    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python3 scripts/run_h43_screen.py            # screen (draws 32/33)
    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python3 scripts/run_h43_screen.py --confirm  # confirmation (34/35)

The confirmation stage exits BEFORE any fit unless at least one arm passed G1 in the screen summary.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import Cell, HGB_PARAMS, load_context  # noqa: E402
from gemsdoe.h43 import H43_NAMES, build_h43_fields, degenerate_fields, prepare_drainage  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "27_preregistered_h43_screen_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "h43_screen"
FOLDS = ("NW", "NE", "SW", "SE")
SCREEN_DRAWS = (32, 33)
CONFIRM_DRAWS = (34, 35)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
HOLDOUT_BEST = 0.14479018210246675  # registry/status_feed.json holdout_best (H34 C1 dot control)
ARMS = ("C0_base", "A1_h43_off_front", "A2_h43_omega_area", "A3_h43_scarp_free", "A4_h43_union")
GATES = dict(
    mean_gain=0.005,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    budget_ratio_band=(0.75, 1.25),
    sgmc_min_positive_folds=3,
    holdout_best=HOLDOUT_BEST,
    min_nonzero_fraction=0.002,
)
ARM_COLUMNS = {
    "C0_base": [],
    "A1_h43_off_front": ["H43_OFF_FRONT", "H43_KNICK"],
    "A2_h43_omega_area": ["H43_LNACC", "H43_OMEGA", "H43_CHANNEL_SCARP"],
    "A3_h43_scarp_free": ["H43_LNACC", "H43_OMEGA", "H43_KNICK", "H43_OFF_FRONT"],
    "A4_h43_union": list(H43_NAMES),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state() -> dict:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"git state unavailable ({exc}); the screen requires a clean committed tree") from exc
    return dict(revision=revision, branch=branch, dirty_worktree=dirty)


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def sgmc_class(data: Path, labels: np.ndarray) -> np.ndarray:
    """Second proxy exactly as in the H34/H35/H41 screens: SGMC pixels that are neither label nor near-label."""
    import rasterio
    from scipy.ndimage import binary_dilation

    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    return sg & ~labels & ~near


def run_cells(ctx, drainage, folds, draws, sink, sgmc_truth: np.ndarray) -> tuple[list[dict], list[str]]:
    from sklearn.ensemble import HistGradientBoostingClassifier

    rows: list[dict] = []
    guard_problems: list[str] = []
    for fold in folds:
        for seed in draws:
            t0 = time.time()
            cell = Cell(ctx, fold, seed, extras=True, h27=True)
            fields, diag = build_h43_fields(
                drainage,
                visible=cell.draw.visible,
                footprint=ctx.foot,
                footprint_idx=ctx.fi,
                scarp_vec=ctx.h27_scarp,
            )
            problems = degenerate_fields(fields, min_nonzero_fraction=GATES["min_nonzero_fraction"])
            if problems:
                guard_problems.append(f"fold={FOLDS[fold]} draw={seed}: " + "; ".join(problems))
            base_n = cell.Xtr.shape[1]
            idx = {n: base_n + i for i, n in enumerate(H43_NAMES)}
            plan = {arm: list(range(base_n)) + [idx[n] for n in cols] for arm, cols in ARM_COLUMNS.items()}
            Xtr = np.concatenate(
                [cell.Xtr] + [fields[i][cell.train_idx][:, None] for i in range(len(H43_NAMES))], axis=1
            )
            Xq = np.concatenate([cell.Xq] + [fields[i][cell.q][:, None] for i in range(len(H43_NAMES))], axis=1)
            del cell.Xtr, cell.Xq
            k = int(round(KFRAC * cell.dom_c.sum()))
            for arm in ARMS:
                t_fit = time.time()
                model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
                model.fit(np.ascontiguousarray(Xtr[:, plan[arm]]), cell.y)
                fit_s = time.time() - t_fit
                t_p = time.time()
                p = model.predict_proba(np.ascontiguousarray(Xq[:, plan[arm]]))[:, 1].astype(np.float32)
                predict_s = time.time() - t_p
                score_crop, candidates = cell.candidates(p, k)
                emitted = score_ordered_dots(score_crop, candidates, MIN_DIST_PX)
                result = cell.evaluate(emitted)
                sg = dti_binary(emitted, sgmc_truth[cell.sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                row = dict(
                    fold=fold,
                    fold_name=FOLDS[fold],
                    draw=seed,
                    arm=arm,
                    **result,
                    sgmc_dti=float(sg["dti"]),
                    sgmc_n_truth=int(sg["n_truth"]),
                    fit_s=fit_s,
                    predict_s=predict_s,
                    n_features=len(plan[arm]),
                    auc=cell.auc(np.nan_to_num(p, nan=0.0)),
                )
                if arm == "C0_base":
                    row["h43_diag"] = diag
                    row["viability_guard"] = problems
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            brief = " ".join(
                f"{a.split('_')[0]}={next(r for r in rows if r['fold'] == fold and r['draw'] == seed and r['arm'] == a)['dti']:.4f}"
                for a in ARMS
            )
            print(f"fold={FOLDS[fold]} draw={seed} {brief}  ({time.time() - t0:.0f}s)", flush=True)
    return rows, guard_problems


def gate_summary(rows: list[dict], folds, draws) -> dict:
    per: dict[str, dict] = {}
    for arm in ARMS[1:]:
        fold_gains, sgmc_gains, budget_ok = [], [], True
        for fold in folds:
            arm_mean = np.mean([r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] in draws])
            ctrl_mean = np.mean(
                [r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] in draws]
            )
            fold_gains.append(float(arm_mean - ctrl_mean))
            a_s = np.mean([r["sgmc_dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] in draws])
            c_s = np.mean(
                [r["sgmc_dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] in draws]
            )
            sgmc_gains.append(float(a_s - c_s))
        pos_draws = []
        for draw in draws:
            n_pos = 0
            for fold in folds:
                a = [r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] == draw]
                c = [r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] == draw]
                if a and c and a[0] - c[0] > 0:
                    n_pos += 1
            pos_draws.append(n_pos)
        for r in rows:
            if r["arm"] == arm and r["draw"] in draws:
                base = next(
                    (x for x in rows if x["arm"] == "C0_base" and x["fold"] == r["fold"] and x["draw"] == r["draw"]),
                    None,
                )
                if base and not (
                    GATES["budget_ratio_band"][0] * base["emitted"]
                    <= r["emitted"]
                    <= GATES["budget_ratio_band"][1] * base["emitted"]
                ):
                    budget_ok = False
        mean_gain = float(np.mean(fold_gains))
        n_arm_cells = len([r for r in rows if r["arm"] == arm and r["draw"] in draws])
        g1 = bool(
            mean_gain >= GATES["mean_gain"]
            and min(pos_draws) >= GATES["min_positive_folds"]
            and min(fold_gains) >= GATES["max_fold_loss"]
            and n_arm_cells == 8
            and budget_ok
        )
        sgmc_pos = int(sum(g > 0 for g in sgmc_gains))
        per[arm] = dict(
            mean_gain=mean_gain,
            fold_gains=fold_gains,
            positive_folds_per_draw=pos_draws,
            worst_fold_gain=min(fold_gains),
            cells_present=n_arm_cells,
            budget_ok=budget_ok,
            sgmc_mean_gain=float(np.mean(sgmc_gains)),
            sgmc_positive_folds=sgmc_pos,
            sgmc_gate_pass=bool(sgmc_pos >= GATES["sgmc_min_positive_folds"]),
            mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == arm and r["draw"] in draws])),
            G1_SCREEN_PASS=g1,
        )
    per["C0_base"] = dict(
        mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["draw"] in draws]))
    )
    return per


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--confirm", action="store_true", help="run confirmation draws (requires a G1 pass in the screen summary)"
    )
    args = ap.parse_args()
    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stage = "confirm" if args.confirm else "screen"
    cells_path = EVIDENCE / f"cells_{stage}.jsonl"
    design_path = EVIDENCE / f"design_{stage}.json"
    summary_path = EVIDENCE / f"summary_{stage}.json"
    if design_path.exists() or cells_path.exists() or summary_path.exists():
        raise SystemExit(f"refusing to overwrite existing {stage} evidence in {EVIDENCE}")
    if args.confirm:
        screen_summary_path = EVIDENCE / "summary_screen.json"
        if not screen_summary_path.is_file():
            raise SystemExit("confirmation requires the screen summary to exist first")
        screen = json.loads(screen_summary_path.read_text())
        passed = [arm for arm in ARMS[1:] if screen["arms"].get(arm, {}).get("G1_SCREEN_PASS")]
        if not passed:
            print("No arm passed G1 on the screen; confirmation exits before any fit.", flush=True)
            return 0
        print(f"confirmation authorised for: {passed}", flush=True)
    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    inputs = {
        r: data / r
        for r in ("labels.tif", "sample_submission.tif", "training_features.tif", "external/derived_sgmc_faults_100m_u8.tif")
    }
    missing = [str(p) for p in inputs.values() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing restored owner-mirror inputs: {missing}")
    elev_npy = work / "bands" / "12_det_elev.npy"
    for p in (elev_npy, work / "static_ABCD.npy", work / "addons.npy"):
        if not p.is_file():
            raise SystemExit(f"missing feature cache {p}; run scripts/prepare_data.py and scripts/build_features.py first")

    folds = [0, 1, 2, 3]
    draws = list(CONFIRM_DRAWS if args.confirm else SCREEN_DRAWS)

    t_start = time.time()
    ctx = load_context(work)
    elev = np.load(elev_npy)
    drainage = prepare_drainage(elev, ctx.foot)
    sgmc_truth = sgmc_class(data, ctx.labels)

    design = dict(
        stage=stage,
        experiment="H43 drainage-network organization: stream-power residual and knickpoint excess",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        folds=[FOLDS[f] for f in folds],
        draws=draws,
        arms=list(ARMS),
        gates=GATES,
        arm_columns=ARM_COLUMNS,
        h43_names=list(H43_NAMES),
        constants=dict(
            k_frac=KFRAC,
            min_dist_px=MIN_DIST_PX,
            emit="frozen H34 C0 (ridge NMS -> drop visible -> topK -> score-ordered Poisson 2.4)",
        ),
        draw_seed_inventory={
            "used_before": "0-13 main/H31/H29, 14-15 factorial, 20-21 H34, 22-23 H31b, 24-27 H35/H40, 28-31 H41",
            "this_stage": draws,
        },
        drainage=dict(elev_band_sha256=sha256_file(elev_npy), **drainage.diagnostics),
        git=state,
        environment=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            packages={n: package_version(n) for n in ("scipy", "scikit-learn", "rasterio")},
        ),
        inputs={r: dict(sha256=sha256_file(p), bytes=p.stat().st_size) for r, p in inputs.items()},
        caches={
            p.name: dict(sha256=sha256_file(work / p.name))
            for p in (
                Path("static_ABCD.npy"),
                Path("static_ABCD.npy.names.json"),
                Path("addons.npy"),
                Path("addons.npy.names.json"),
            )
        },
        modules={
            f"gemsdoe/{m}": sha256_file(ROOT / "src/gemsdoe" / m)
            for m in ("h43.py", "experiment.py", "thinning.py", "metric.py", "features.py")
        },
    )
    design_path.write_text(json.dumps(design, indent=2) + "\n")
    print(
        f"design recorded: {design_path} (git {state['revision'][:8]}, {len(draws)} draws x {len(folds)} folds x {len(ARMS)} arms)",
        flush=True,
    )

    sink = cells_path.open("w")
    try:
        rows, guard_problems = run_cells(ctx, drainage, folds, draws, sink, sgmc_truth)
    finally:
        sink.close()
    per = gate_summary(rows, folds, draws)
    summary = dict(
        stage=stage,
        draws=draws,
        folds=[FOLDS[f] for f in folds],
        arms=per,
        n_cells=len(rows),
        elapsed_s=round(time.time() - t_start, 2),
        viability_guard=dict(
            min_nonzero_fraction=GATES["min_nonzero_fraction"],
            problems=guard_problems,
            passed=not guard_problems,
        ),
        note=(
            "DTI proxies on blocked holdout folds; gates frozen in knowledge/27 §4 (G1 screen, G2 confirmation, "
            "G3 promotion requiring both holdout_best and SGMC >= 3/4 positive folds in both stages)."
        ),
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {
                a: {k: v for k, v in e.items() if k in ("mean_gain", "worst_fold_gain", "G1_SCREEN_PASS", "sgmc_gate_pass", "mean_dti")}
                for a, e in per.items()
            },
            indent=2,
        )
    )
    if guard_problems:
        print(
            f"VIABILITY GUARD FAILED ({len(guard_problems)} cells): columns too sparse to move a model:\n  "
            + "\n  ".join(guard_problems),
            flush=True,
        )
    print(f"wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
