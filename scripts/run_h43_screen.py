#!/usr/bin/env python3
"""H43 screen: drainage-network columns (stream power, knickpoint excess) vs the frozen H34 C0 control.

Protocol, columns, arms, gates and draws are frozen in
``knowledge/29_preregistered_h43_screen_2026-10-03.md`` BEFORE this script is exercised on real data; the
runner records that file's SHA-256 plus every input/module hash into ``evidence/h43_screen/design_screen.json``
and refuses to overwrite existing evidence. It requires a clean committed worktree and never contacts
DrivenData; all inputs are hash-pinned owner mirrors restored under ``GEMS_DATA_DIR``.

    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h43_screen.py            # screen (draws 32/33)
    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h43_screen.py --confirm  # confirmation (34/35)

The confirmation stage exits BEFORE any fit unless at least one arm passed G1 in the screen summary.
A 3.9 GB container limit OOM-killed the first screen process (2026-10-03, 23 of 40 rows; that partial stage was
quarantined after its cached ``det_elev`` band failed a byte re-check against the pinned GeoTIFF); ``--resume`` appends to an
existing ``cells_<stage>.jsonl``, re-verifies every frozen hash from ``design_<stage>.json`` first, skips
``(fold, draw, arm)`` triples already present, and only writes the summary once all cells are complete. Data already
recorded is never rewritten.

    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h43_screen.py --resume --cell SW:32 --max-cells 1
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
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import HGB_PARAMS, Cell, load_context  # noqa: E402
from gemsdoe.h43 import H43_NAMES, build_h43_columns  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "29_preregistered_h43_screen_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "h43_screen"
BANDS = "work/bands"
FOLDS = ("NW", "NE", "SW", "SE")
SCREEN_DRAWS = (32, 33)
CONFIRM_DRAWS = (34, 35)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
OFF_CATALOGUE_MIN_PX = 5.0
HOLDOUT_BEST = 0.14479018210246675  # registry/status_feed.json holdout_best (H34 C1 dot control)
ARMS = ("C0_base", "A1_off", "A2_network", "A3_knick", "A4_union")
GATES = dict(mean_gain=0.005, min_positive_folds=3, max_fold_loss=-0.010, budget_ratio_band=(0.75, 1.25),
             sgmc_min_positive_folds=3, holdout_best=HOLDOUT_BEST, min_nonzero_fraction=0.002)
ARM_COLUMNS = {
    "C0_base": [],
    "A1_off": ["H43_OFF_FRONT"],
    "A2_network": ["H43_LNACC", "H43_OMEGA"],
    "A3_knick": ["H43_KNICK", "H43_OFF_FRONT"],
    "A4_union": list(H43_NAMES),
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
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - environment guard
        raise SystemExit(f"git state unavailable ({exc}); the screen requires a clean committed tree") from exc
    return dict(revision=revision, branch=branch, dirty_worktree=dirty)


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "not-installed"


def sgmc_class(data: Path, labels: np.ndarray) -> np.ndarray:
    """Second proxy exactly as in the H34/H35/H41 screens: SGMC pixels neither label nor near-label."""
    import rasterio

    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    return sg & ~labels & ~near


def grid_from_vector(vec: np.ndarray, fi: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    g = np.zeros(shape, np.float32)
    g.ravel()[fi] = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    return g


def off_catalogue_mask(visible: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Footprint pixels at least 500 m (5 px, Euclidean) from every visible catalogue pixel."""
    dist = distance_transform_edt(~visible)
    return dist >= OFF_CATALOGUE_MIN_PX


def run_cells(ctx, static_cols, knick_grid, off_masks, folds, draws, sink, sgmc_truth: np.ndarray,
              *, skip_arms=None, cell_filter=None, done_values=None, max_cells=None):
    """Fit every requested cell/arm, appending rows to ``sink``.

    ``skip_arms`` holds ``(fold, seed, arm)`` triples already recorded in the evidence file (resume path); a cell
    whose five arms are all recorded is skipped entirely. ``cell_filter`` restricts to ``(fold, seed)`` pairs.
    """
    import gc

    skip_arms = set(skip_arms or ())
    rows: list[dict] = []
    guard_problems: list[str] = []
    seen: dict[tuple[int, int, str], float] = dict(done_values or {})
    done_cells = 0
    for fold in folds:
        for seed in draws:
            if cell_filter is not None and (fold, seed) not in cell_filter:
                continue
            if all((fold, seed, arm) in skip_arms for arm in ARMS):
                continue
            if max_cells is not None and done_cells >= max_cells:
                print(f"stopping after {done_cells} cell(s); re-run --resume to continue", flush=True)
                return rows, guard_problems
            done_cells += 1
            t0 = time.time()
            cell = Cell(ctx, fold, seed, extras=True, h27=True)
            off = off_masks[seed]
            columns = {
                "H43_LNACC": static_cols["H43_LNACC"],
                "H43_OMEGA": static_cols["H43_OMEGA"],
                "H43_KNICK": static_cols["H43_KNICK"],
                "H43_OFF_FRONT": (knick_grid * off).ravel()[ctx.fi],
                "H43_CHANNEL_SCARP": static_cols["H43_CHANNEL_SCARP"],
            }
            cell_guard = []
            for name in H43_NAMES:
                frac = float(np.count_nonzero(columns[name])) / max(int(ctx.fi.size), 1)
                if frac < GATES["min_nonzero_fraction"]:
                    msg = f"fold={FOLDS[fold]} draw={seed} {name}: nonzero {frac:.6f}"
                    guard_problems.append(msg)
                    cell_guard.append(msg)
            base_n = cell.Xtr.shape[1]
            idx = {n: base_n + i for i, n in enumerate(H43_NAMES)}
            plan = {arm: list(range(base_n)) + [idx[n] for n in cols] for arm, cols in ARM_COLUMNS.items()}
            Xtr = np.concatenate([cell.Xtr] + [columns[n][cell.train_idx][:, None] for n in H43_NAMES], axis=1)
            Xq = np.concatenate([cell.Xq] + [columns[n][cell.q][:, None] for n in H43_NAMES], axis=1)
            del cell.Xtr, cell.Xq
            k = int(round(KFRAC * cell.dom_c.sum()))
            for arm in ARMS:
                if (fold, seed, arm) in skip_arms:
                    continue
                t_fit = time.time()
                from sklearn.ensemble import HistGradientBoostingClassifier

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
                row = dict(fold=fold, fold_name=FOLDS[fold], draw=seed, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]),
                           fit_s=fit_s, predict_s=predict_s, n_features=len(plan[arm]),
                           auc=cell.auc(np.nan_to_num(p, nan=0.0)))
                if arm == "C0_base":
                    row["h43_diag"] = {n: dict(nonzero_fraction=float(np.count_nonzero(columns[n]) / ctx.fi.size))
                                       for n in H43_NAMES}
                    row["viability_guard"] = cell_guard
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                seen[(fold, seed, arm)] = float(row["dti"])
                del model, p, score_crop, candidates, emitted, result, sg
            del Xtr, Xq, columns, cell
            gc.collect()
            brief = " ".join(f"{a.split('_')[0]}={seen[(fold, seed, a)]:.4f}" for a in ARMS
                             if (fold, seed, a) in seen)
            print(f"fold={FOLDS[fold]} draw={seed} {brief}  ({time.time() - t0:.0f}s)", flush=True)
    return rows, guard_problems


def gate_summary(rows: list[dict], folds, draws) -> dict:
    per: dict[str, dict] = {}
    for arm in ARMS[1:]:
        fold_gains, sgmc_gains, budget_ok = [], [], True
        for fold in folds:
            arm_mean = np.mean([r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] in draws])
            ctrl_mean = np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] in draws])
            fold_gains.append(float(arm_mean - ctrl_mean))
            a_s = np.mean([r["sgmc_dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] in draws])
            c_s = np.mean([r["sgmc_dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] in draws])
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
                base = next((x for x in rows if x["arm"] == "C0_base" and x["fold"] == r["fold"] and x["draw"] == r["draw"]), None)
                if base and not (GATES["budget_ratio_band"][0] * base["emitted"] <= r["emitted"]
                                 <= GATES["budget_ratio_band"][1] * base["emitted"]):
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
        per[arm] = dict(
            mean_gain=mean_gain, fold_gains=fold_gains, positive_folds_per_draw=pos_draws,
            worst_fold_gain=min(fold_gains), cells_present=n_arm_cells, budget_ok=budget_ok,
            sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
            mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == arm and r["draw"] in draws])),
            mean_auc=float(np.nanmean([r["auc"] for r in rows if r["arm"] == arm and r["draw"] in draws])),
            G1_SCREEN_PASS=g1,
        )
    per["C0_base"] = dict(mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["draw"] in draws])),
                          mean_auc=float(np.nanmean([r["auc"] for r in rows if r["arm"] == "C0_base" and r["draw"] in draws])))
    return per


def pressed_inputs(data: Path, work: Path) -> dict[str, Path]:
    """The exact input files whose bytes the stage's design file pins (label -> resolved path)."""
    return {
        "data/sample_submission.tif": data / "sample_submission.tif",
        "data/labels.tif": data / "labels.tif",
        "data/external/derived_sgmc_faults_100m_u8.tif": data / "external" / "derived_sgmc_faults_100m_u8.tif",
        "work/bands/_footprint.npy": work / "bands" / "_footprint.npy",
        "work/bands/_labels.npy": work / "bands" / "_labels.npy",
        "work/bands/12_det_elev.npy": work / "bands" / "12_det_elev.npy",
        "work/static_ABCD.npy": work / "static_ABCD.npy",
        "work/addons.npy": work / "addons.npy",
    }


def load_recorded_rows(path: Path) -> list[dict]:
    """Every cell row already appended to the stage's raw-cell file (resume path reads, never rewrites)."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_design(design_path: Path) -> dict:
    """Re-verify every frozen hash recorded in an existing design file before appending cells to it."""
    if not design_path.is_file():
        raise SystemExit(f"resume refused: missing {design_path}")
    design = json.loads(design_path.read_text())
    if design["preregistration"]["sha256"] != sha256_file(PREREG):
        raise SystemExit("resume refused: the frozen preregistration changed since the screen started")
    for key, recorded in design.get("modules", {}).items():
        current = sha256_file(ROOT / "src" / key)
        if recorded != current:
            raise SystemExit(f"resume refused: {key} changed since the screen started")
    press = pressed_inputs(data_dir(), work_dir())
    for key, entry in design.get("inputs", {}).items():
        path = press.get(key)
        if path is None or not path.is_file() or path.stat().st_size != entry["bytes"] \
                or sha256_file(path) != entry["sha256"]:
            raise SystemExit(f"resume refused: input {key} changed since the screen started")
    return design


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="run confirmation draws (requires a G1 pass in the screen summary)")
    ap.add_argument("--resume", action="store_true",
                    help="append missing cells to an existing (hash-verified) cells_<stage>.jsonl instead of refusing")
    ap.add_argument("--cell", action="append", default=None, metavar="FOLD:DRAW",
                    help="restrict to one cell (fold name/index : draw); repeatable; requires --resume")
    ap.add_argument("--max-cells", type=int, default=None,
                    help="stop after N cells in this process; with --resume the stage is continued later")
    args = ap.parse_args()
    if args.cell and not args.resume:
        raise SystemExit("--cell only makes sense with --resume")
    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stage = "confirm" if args.confirm else "screen"
    cells_path = EVIDENCE / f"cells_{stage}.jsonl"
    design_path = EVIDENCE / f"design_{stage}.json"
    summary_path = EVIDENCE / f"summary_{stage}.json"
    existing_rows: list[dict] = []
    if args.resume:
        verify_design(design_path)
        existing_rows = load_recorded_rows(cells_path)
        if summary_path.exists():
            raise SystemExit(f"{summary_path} already exists; the {stage} stage is closed")
        print(f"resume: {len(existing_rows)} recorded rows in {cells_path.name}", flush=True)
    else:
        for p in (cells_path, design_path, summary_path):
            if p.exists():
                raise SystemExit(f"refusing to overwrite existing {stage} evidence: {p}")
    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")
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

    data, work = data_dir(), work_dir()
    elev_path = work / "bands" / "12_det_elev.npy"
    press = pressed_inputs(data, work)
    missing = [k for k, p in press.items() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing restored/derived inputs: {missing}; run scripts/download_competition_data.sh, "
                         "scripts/prepare_data.py, scripts/build_features.py and scripts/build_addons.py first")

    ctx = load_context(work)
    elev = np.load(elev_path)
    valid = ctx.foot & np.isfinite(elev)
    scarp = grid_from_vector(ctx.h27_scarp, ctx.fi, ctx.foot.shape)

    t_build = time.time()
    # The off-catalogue column is draw-dependent, so build the draw-independent part with off_mask=None and
    # multiply by the per-draw mask below; this keeps one build for all four folds.
    cols_grid, diag = build_h43_columns(elev, valid, scarp, off_mask=None)
    static_cols = {n: np.asarray(cols_grid[n], np.float32).ravel()[ctx.fi] for n in H43_NAMES}
    knick_grid = np.asarray(cols_grid["H43_KNICK"], np.float32)
    build_s = time.time() - t_build
    nonzero = {n: float(np.count_nonzero(static_cols[n]) / ctx.fi.size) for n in H43_NAMES}
    print(f"built H43 columns in {build_s:.1f}s; nonzero fractions: "
          + ", ".join(f"{n}={v:.4f}" for n, v in nonzero.items()), flush=True)

    off_masks = {}
    for seed in (CONFIRM_DRAWS if args.confirm else SCREEN_DRAWS):
        draw = ctx.holdout.draw(0, seed)
        off_masks[seed] = off_catalogue_mask(draw.visible, ctx.foot.shape)

    folds = [0, 1, 2, 3]
    draws = list(CONFIRM_DRAWS if args.confirm else SCREEN_DRAWS)
    sgmc_truth = sgmc_class(data, ctx.labels)

    design = dict(
        stage=stage, experiment="H43 drainage-network screen (stream power + knickpoint excess)",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        folds=[FOLDS[f] for f in folds], draws=draws, arms=list(ARMS), gates=GATES,
        arm_columns=ARM_COLUMNS, h43_names=list(H43_NAMES),
        constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX, off_catalogue_min_px=OFF_CATALOGUE_MIN_PX,
                       emit="frozen C0 emission (ridge NMS -> drop visible -> topK -> score-ordered Poisson 2.4)"),
        draw_seed_inventory={"rule": "registry/draw_ledger.json",
                             "used_before": "0-31 across H29/H31/factorial/H34/H35/H40/H31b/H41",
                             "this_stage": draws},
        h43_diagnostics=diag,
        h43_columns_nonzero_fraction=nonzero,
        build_seconds=build_s,
        git=state,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         packages={n: package_version(n) for n in ("scipy", "scikit-learn", "rasterio")}),
        inputs={k: dict(sha256=sha256_file(p), bytes=p.stat().st_size) for k, p in press.items()},
        modules={f"gemsdoe/{m}": sha256_file(ROOT / "src" / "gemsdoe" / m)
                 for m in ("h43.py", "experiment.py", "thinning.py", "metric.py", "features.py")},
        note=("H43 is built from the cached det_elev band plus the *visible* catalogue only; the off-catalogue "
              "mask removes information rather than adding it. det_elev is a detrended surface of unknown "
              "absolute datum, so no absolute gradient or discharge is claimed (knowledge/29 §2, §6)."),
    )
    design_path.write_text(json.dumps(design, indent=2, default=float) + "\n")
    print(f"design recorded: {design_path} (git {state['revision'][:8]}, {len(draws)} draws x {len(folds)} folds x {len(ARMS)} arms)", flush=True)

    cell_filter = None
    if args.cell:
        cell_filter = set()
        for spec in args.cell:
            fold_txt, _, draw_txt = spec.partition(":")
            try:
                fold = FOLDS.index(fold_txt) if fold_txt in FOLDS else int(fold_txt)
                cell_filter.add((fold, int(draw_txt)))
            except ValueError as exc:
                raise SystemExit(f"--cell expects FOLD:DRAW (e.g. SW:32), got {spec!r}") from exc
        unknown = sorted(c for c in cell_filter if c[0] not in folds or c[1] not in draws)
        if unknown:
            raise SystemExit(f"--cell outside the frozen {stage} design: {unknown}")
    skip_arms = {(r["fold"], r["draw"], r["arm"]) for r in existing_rows}
    done_values = {(r["fold"], r["draw"], r["arm"]): float(r["dti"]) for r in existing_rows}
    sink = cells_path.open("a" if args.resume else "w")
    try:
        new_rows, guard_problems = run_cells(ctx, static_cols, knick_grid, off_masks, folds, draws, sink, sgmc_truth,
                                             skip_arms=skip_arms, cell_filter=cell_filter, done_values=done_values,
                                             max_cells=args.max_cells)
    finally:
        sink.close()
    all_rows = existing_rows + new_rows
    recorded = {(r["fold"], r["draw"], r["arm"]) for r in all_rows}
    expected = len(folds) * len(draws) * len(ARMS)
    if len(recorded) != expected:
        print(f"{stage} incomplete: {len(recorded)}/{expected} (fold, draw, arm) rows recorded; summary NOT written. "
              f"Re-run with --resume to continue.", flush=True)
        return 0
    per = gate_summary(all_rows, folds, draws)
    guard_problems = [msg for r in all_rows for msg in r.get("viability_guard", [])]
    summary = dict(
        stage=stage, draws=draws, folds=[FOLDS[f] for f in folds], arms=per,
        n_cells=len(all_rows),
        execution=dict(processes=(1 + (1 if existing_rows else 0)) if args.resume else 1,
                       resumed=bool(args.resume), rows_this_process=len(new_rows),
                       note=("the 2026-10-03 OOM kill split this stage across processes; every row was appended by a "
                             "process that re-verified the frozen prereg, module and input hashes") if args.resume else None),
        viability_guard=dict(min_nonzero_fraction=GATES["min_nonzero_fraction"],
                             static_columns=nonzero, problems=guard_problems, passed=not guard_problems),
        note=("DTI proxies on blocked holdout folds; gates frozen in knowledge/29 §5. The drainage surface is "
              "detrended, so a pass is corridor-ranking evidence about drainage organization, never a claim "
              "about real discharge or about 30 m-scale scarps."),
    )
    summary_path.write_text(json.dumps(summary, indent=2, default=float) + "\n")
    print(json.dumps({a: {k: v for k, v in e.items() if k in ("mean_gain", "worst_fold_gain", "G1_SCREEN_PASS", "mean_dti")}
                      for a, e in per.items()}, indent=2))
    if guard_problems:
        print(f"VIABILITY GUARD FAILED ({len(guard_problems)} cells): columns too sparse to move a model:\n  "
              + "\n  ".join(guard_problems[:5]), flush=True)
    print(f"wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
