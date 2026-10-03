#!/usr/bin/env python3
"""H35/H40 paired screen: interaction-zone and dense-persistence columns vs the frozen H34 C0 control.

Protocol, arms, gates and draws are frozen in
``knowledge/19_preregistered_h35_h40_screen_2026-10-03.md`` BEFORE this script runs; the runner records that
file's SHA-256 plus source/input hashes into ``evidence/h35_h40_screen/design.json`` and refuses to
overwrite existing evidence. It requires a clean committed worktree. Nothing here contacts DrivenData; all
inputs are the hash-pinned owner mirrors restored under GEMS_DATA_DIR.

    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python3 scripts/run_h35_screen.py            # screen (draws 24/25)
    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python3 scripts/run_h35_screen.py --confirm  # confirmation (26/27)

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

from gemsdoe.experiment import Cell, load_context  # noqa: E402
from gemsdoe.dense_persist import HP_NAMES  # noqa: E402
from gemsdoe.h35 import H35_NAMES, build_interaction_zone_fields  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "19_preregistered_h35_h40_screen_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "h35_h40_screen"
FOLDS = ("NW", "NE", "SW", "SE")
SCREEN_DRAWS = (24, 25)
CONFIRM_DRAWS = (26, 27)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
HOLDOUT_BEST = 0.14479018210246675  # H34 C1 geodesic-dot control, evidence/h34_coverage_screen/summary.json
ARMS = ("C0_base", "A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union")
GATES = dict(mean_gain=0.005, min_positive_folds=3, max_fold_loss=-0.010, budget_ratio_band=(0.75, 1.25),
             sgmc_min_positive_folds=3, holdout_best=HOLDOUT_BEST)


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


def load_hp_cache(work: Path) -> tuple[np.ndarray, list[str], dict]:
    cache = work / "h40_dense_persistence.npy"
    names_p = Path(str(cache) + ".names.json")
    meta_p = Path(str(cache) + ".metadata.json")
    for path in (cache, names_p, meta_p):
        if not path.is_file():
            raise SystemExit(f"missing H40 cache {path.name}; run scripts/build_h40_features.py first")
    meta = json.loads(meta_p.read_text())
    names = json.loads(names_p.read_text())
    fields = np.load(cache, mmap_mode="r")
    if float(fields.min()) < 0.0 or float(fields.max()) > 1.0:
        raise SystemExit("H40 cache violated [0,1]")
    return np.asarray(fields), names, meta


def cell_features(ctx, cell: Cell, hp: np.ndarray) -> tuple[dict, dict]:
    """Per-cell H35 (visible-only) + H40 (static) columns, quadrant-vector aligned."""
    d = cell.draw
    h35, diag = build_interaction_zone_fields(d.visible, ctx.foot, ctx.fi)
    nb = cell.Xtr.shape[1]
    scarp_col = nb - 2          # H27 block order: tip, scarp, tip*scarp
    mh = ctx.nscale("A_mag_hg_ridge", cell.Xq[:, ctx.col["A_mag_hg_ridge"]])
    gh = ctx.nscale("A_grav_hg_ridge", cell.Xq[:, ctx.col["A_grav_hg_ridge"]])
    pfg = np.sqrt(np.clip(mh * gh, 0.0, 1.0)).astype(np.float32)
    q = cell.q
    relay_td = h35[1][q]
    out = {
        "H35_RELAY": h35[0][q],
        "H35_RELAY_TD": relay_td,
        "H35_JUNCTION": h35[2][q],
        "H35_TIPDENS": h35[3][q],
        "H35_RELAY_TD_X_SCARP": (relay_td * cell.Xq[:, scarp_col]).astype(np.float32),
        "H35_RELAY_TD_X_PFG": (relay_td * pfg).astype(np.float32),
        "HP_MAG": hp[0][q], "HP_GRAV": hp[1][q], "HP_MIN": hp[2][q], "HP_DEEP": hp[3][q],
    }
    # training-side copies (same columns, training indices)
    tr = {
        "H35_RELAY_t": h35[0][cell.train_idx],
        "H35_RELAY_TD_t": h35[1][cell.train_idx],
        "H35_JUNCTION_t": h35[2][cell.train_idx],
        "H35_TIPDENS_t": h35[3][cell.train_idx],
        "H35_RELAY_TD_X_SCARP_t": (h35[1][cell.train_idx] * cell.Xtr[:, scarp_col]).astype(np.float32),
        "H35_RELAY_TD_X_PFG_t": (h35[1][cell.train_idx] * np.sqrt(np.clip(
            ctx.nscale("A_mag_hg_ridge", cell.Xtr[:, ctx.col["A_mag_hg_ridge"]])
            * ctx.nscale("A_grav_hg_ridge", cell.Xtr[:, ctx.col["A_grav_hg_ridge"]]), 0.0, 1.0))).astype(np.float32),
        "HP_MAG_t": hp[0][cell.train_idx], "HP_GRAV_t": hp[1][cell.train_idx],
        "HP_MIN_t": hp[2][cell.train_idx], "HP_DEEP_t": hp[3][cell.train_idx],
    }
    out.update(tr)
    diag["visible_pixels_used"] = int(d.visible.sum())
    return out, diag


def arm_columns(base_n: int) -> dict[str, list[int]]:
    """Column index plan: P0 first, then appended H35/H40 columns per arm."""
    a1 = ["H35_RELAY", "H35_RELAY_TD", "H35_JUNCTION", "H35_TIPDENS"]
    a2 = a1 + ["H35_RELAY_TD_X_SCARP", "H35_RELAY_TD_X_PFG"]
    a3 = ["HP_MAG", "HP_GRAV", "HP_MIN", "HP_DEEP"]
    a4 = a2 + a3
    order = a1 + ["H35_RELAY_TD_X_SCARP", "H35_RELAY_TD_X_PFG"] + a3  # appends layout
    idx = {n: base_n + i for i, n in enumerate(order)}
    return {
        "C0_base": list(range(base_n)),
        "A1_h35_struct": list(range(base_n)) + [idx[n] for n in a1],
        "A2_h35_corrob": list(range(base_n)) + [idx[n] for n in a2],
        "A3_h40_persist": list(range(base_n)) + [idx[n] for n in a3],
        "A4_union": list(range(base_n)) + [idx[n] for n in a4],
    }


def sgmc_class(data: Path, labels: np.ndarray) -> np.ndarray:
    from scipy.ndimage import binary_dilation
    import rasterio

    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    return sg & ~labels & ~near


def run_cells(ctx, hp: np.ndarray, hp_names: list[str], folds, draws, sink, sgmc_truth: np.ndarray) -> list[dict]:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from gemsdoe.experiment import HGB_PARAMS

    rows: list[dict] = []
    for fold in folds:
        for seed in draws:
            t0 = time.time()
            cell = Cell(ctx, fold, seed, extras=True, h27=True)
            feats, h35_diag = cell_features(ctx, cell, hp)
            base_n = cell.Xtr.shape[1]
            extra_names = ["H35_RELAY", "H35_RELAY_TD", "H35_JUNCTION", "H35_TIPDENS",
                           "H35_RELAY_TD_X_SCARP", "H35_RELAY_TD_X_PFG",
                           "HP_MAG", "HP_GRAV", "HP_MIN", "HP_DEEP"]
            assert extra_names[:4] == H35_NAMES and hp_names == list(HP_NAMES)  # frozen column order
            Xtr = np.concatenate([cell.Xtr] + [feats[f"{n}_t"][:, None] for n in extra_names], axis=1)
            Xq = np.concatenate([cell.Xq] + [feats[n][:, None] for n in extra_names], axis=1)
            del cell.Xtr, cell.Xq
            plan = arm_columns(base_n)
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
                row = dict(fold=fold, fold_name=FOLDS[fold], draw=seed, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]),
                           fit_s=fit_s, predict_s=predict_s,
                           auc=cell.auc(np.nan_to_num(p, nan=0.0)))
                if arm == "C0_base":
                    row["h35_diag"] = h35_diag
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            elapsed = time.time() - t0
            brief = " ".join(f"{a.split('_')[0]}={next(r for r in rows if r['fold'] == fold and r['draw'] == seed and r['arm'] == a)['dti']:.4f}" for a in ARMS)
            print(f"fold={FOLDS[fold]} draw={seed} {brief}  ({elapsed:.0f}s)", flush=True)
    return rows


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
                if base and not (GATES["budget_ratio_band"][0] * base["emitted"] <= r["emitted"] <= GATES["budget_ratio_band"][1] * base["emitted"]):
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
            G1_SCREEN_PASS=g1,
        )
    per["C0_base"] = dict(mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["draw"] in draws])))
    return per


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="run confirmation draws (requires a G1 pass in the screen summary)")
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
    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    inputs = {r: data / r for r in ("labels.tif", "sample_submission.tif", "training_features.tif",
                                    "external/derived_sgmc_faults_100m_u8.tif")}
    missing = [str(p) for p in inputs.values() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing restored owner-mirror inputs: {missing}")

    screen_summary_path = EVIDENCE / "summary_screen.json"
    if args.confirm:
        if not screen_summary_path.is_file():
            raise SystemExit("confirmation requires the screen summary to exist first")
        screen = json.loads(screen_summary_path.read_text())
        passed = [arm for arm in ARMS[1:] if screen["arms"].get(arm, {}).get("G1_SCREEN_PASS")]
        if not passed:
            print("No arm passed G1 on the screen; confirmation exits before any fit.", flush=True)
            return 0
        print(f"confirmation authorised for: {passed}", flush=True)
    folds = [0, 1, 2, 3]
    draws = list(CONFIRM_DRAWS if args.confirm else SCREEN_DRAWS)

    design = dict(
        stage=stage, experiment="H35/H40 interaction-zone & dense-persistence screen",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        folds=[FOLDS[f] for f in folds], draws=draws,
        arms=list(ARMS), gates=GATES,
        constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX, emit="frozen H34 C0 (ridge NMS -> drop visible -> topK -> score-ordered Poisson 2.4)"),
        draw_seed_inventory={"used_before": "0-13 main/H31/H29, 14-15 factorial, 20-21 H34/C0, 24-25 this screen, 26-27 this confirmation", "this_stage": draws},
        git=state,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         packages={n: package_version(n) for n in ("scipy", "scikit-learn", "rasterio")}),
        inputs={r: dict(sha256=sha256_file(p), bytes=p.stat().st_size) for r, p in inputs.items()},
        modules={
            "gemsdoe/h35.py": sha256_file(ROOT / "src/gemsdoe/h35.py"),
            "gemsdoe/dense_persist.py": sha256_file(ROOT / "src/gemsdoe/dense_persist.py"),
            "gemsdoe/experiment.py": sha256_file(ROOT / "src/gemsdoe/experiment.py"),
        },
    )
    hp, hp_names, hp_meta = load_hp_cache(work)
    design["h40_cache"] = dict(sha256=sha256_file(work / "h40_dense_persistence.npy"), names=hp_names,
                               metadata=hp_meta)
    if hp_meta["preregistration"]["sha256"] != design["preregistration"]["sha256"]:
        raise SystemExit("H40 cache was built against a different preregistration document")
    design_path.write_text(json.dumps(design, indent=2) + "\n")

    ctx = load_context(work)
    sgmc_truth = sgmc_class(data, ctx.labels)
    print(f"H35/H40 {stage}: folds {folds}, draws {draws}; SGMC off-catalogue truth {int(sgmc_truth.sum()):,} px", flush=True)
    t0 = time.time()
    with cells_path.open("w", encoding="utf-8") as sink:
        rows = run_cells(ctx, hp, hp_names, folds, draws, sink, sgmc_truth)
    per = gate_summary(rows, folds, draws)
    elapsed = time.time() - t0
    if not args.confirm:
        for arm in ARMS[1:]:
            per[arm]["G3_holdout_check_note"] = "screen stage does not evaluate G3; see summary + promotion doc"
    else:
        screen = json.loads(screen_summary_path.read_text())
        for arm in ARMS[1:]:
            g1s = screen["arms"].get(arm, {}).get("G1_SCREEN_PASS", False)
            g1c = per[arm]["G1_SCREEN_PASS"]
            per[arm]["G2_CONFIRM_PASS"] = bool(g1s and g1c)
            per[arm]["G3_slot_eligible"] = bool(
                per[arm]["G2_CONFIRM_PASS"]
                and per[arm]["mean_dti"] > GATES["holdout_best"]
                and screen["arms"][arm]["mean_dti"] > GATES["holdout_best"]
                and per[arm]["sgmc_positive_folds"] >= GATES["sgmc_min_positive_folds"]
            )
    summary = dict(stage=stage, elapsed_s=elapsed, arms=per,
                   gates=GATES, git=state,
                   interpretation=("Proxy outcome only: masked DTI on hidden catalogue components plus an SGMC off-catalogue class. "
                                   "Neither is the organizer metric; no competition score is claimed or implied."))
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({arm: {k: v for k, v in per[arm].items() if k in ("mean_gain", "G1_SCREEN_PASS")} for arm in ARMS[1:]}, indent=2))
    print(f"elapsed {elapsed:.1f}s -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
