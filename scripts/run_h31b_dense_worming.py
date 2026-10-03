#!/usr/bin/env python3
"""Run the frozen H31b dense worming paired spatial screen or fresh confirmation.

Frozen design: knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md. This command never
contacts DrivenData. Refuses to fit outside an Arena session branch with a clean worktree, and
refuses to overwrite existing evidence. The confirmation stage additionally requires a PASS
screen summary and identical frozen inputs.

    python scripts/run_h31b_dense_worming.py --stage screen     # draws 22,23 (frozen)
    python scripts/run_h31b_dense_worming.py --stage confirm    # draws 24,25 (frozen)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
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

from gemsdoe.experiment import Cell, HGB_PARAMS, load_context  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.wormdense import W_NAMES  # noqa: E402

FOLDS = {0: "NW", 1: "NE", 2: "SW", 3: "SE"}
STAGE_DRAWS = {"screen": [22, 23], "confirm": [24, 25]}
ARMS = ("C_base", "C_wrtp", "C_wpsg", "C_wgrav", "C_wall")
PRIMARY = "C_wall"
KFRAC = 0.0245
DOT_MIN_DIST = 2.4
PREREG_PATH = ROOT / "knowledge" / "19_preregistered_h31b_dense_worming_2026-10-03.md"
HOLDOUT_BEST = 0.14479  # H34 C1 geodesic-dot 8-cell mean (draws 20/21); knowledge/17
GATES = dict(
    min_mean_gain_per_draw=0.005,
    min_positive_folds_per_draw=3,
    max_fold_loss=-0.010,
    holdout_best=HOLDOUT_BEST,
)
ARENA_BRANCH_RE = re.compile(r"^arena/[0-9a-f]{8}-gemsdoe29$")


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

    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"),
                dirty=bool(run("status", "--porcelain")))


def require_clean_fixed_branch() -> tuple[str, str]:
    """Refuse to fit outside an Arena session branch of this repository with a clean worktree."""
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if not ARENA_BRANCH_RE.match(branch):
        raise SystemExit(f"refusing to fit outside an Arena session branch of this repository; found {branch!r}")
    if status.strip():
        raise SystemExit("refusing to fit with a dirty worktree; freeze the preregistration, code, and tests first")
    return branch, revision


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


def verify_restored_inputs(data: Path) -> dict:
    receipt_path = data / "restore_receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        bad = [r["id"] for r in receipt.get("files", receipt if isinstance(receipt, list) else [])
               if isinstance(r, dict) and r.get("status") not in ("present", "restored")]
        if bad:
            raise SystemExit(f"restore receipt reports problems: {bad}")
    else:
        print("note: no restore receipt; verifying manifest pins directly", file=sys.stderr)
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    pins = {f["dest"]: f["sha256"] for f in manifest["files"]}
    out = {}
    for dest, want in pins.items():
        p = data / dest
        if not p.is_file():
            raise SystemExit(f"missing restored input {p}")
        got = sha256_file(p)
        if got != want:
            raise SystemExit(f"input hash mismatch for {dest}: {got} != {want}")
        out[dest] = got
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=("screen", "confirm"), default="screen")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    stage = args.stage
    draws = STAGE_DRAWS[stage]
    out = Path(args.out) if args.out else ROOT / "evidence" / ("h31b_dense_screen" if stage == "screen" else "h31b_dense_confirm")
    cells_path, design_path, summary_path = out / "cells.jsonl", out / "design.json", out / "summary.json"
    if design_path.exists() or cells_path.exists():
        raise SystemExit(f"refusing to overwrite existing evidence in {out}")

    branch, revision = require_clean_fixed_branch()

    # confirmation must inherit a PASS screen with identical frozen design
    frozen_inputs: dict = {}
    if stage == "confirm":
        screen_design = ROOT / "evidence" / "h31b_dense_screen" / "design.json"
        screen_summary = ROOT / "evidence" / "h31b_dense_screen" / "summary.json"
        if not (screen_design.is_file() and screen_summary.is_file()):
            raise SystemExit("screen evidence missing; run the screen stage first")
        sd = json.loads(screen_design.read_text())
        ss = json.loads(screen_summary.read_text())
        if ss.get("pass_fail") != "PASS":
            raise SystemExit(f"screen did not pass ({ss.get('pass_fail')}); confirmation is blocked")
        frozen_inputs = sd.get("frozen_inputs", {})

    data, work = data_dir(), work_dir()
    required = ["training_features.tif", "labels.tif", "sample_submission.tif",
                "external/derived_sgmc_faults_100m_u8.tif"]
    missing = [r for r in required if not (data / r).is_file()]
    if missing:
        raise SystemExit(f"missing restored owner-mirror inputs: {missing}; run scripts/restore_h31_data.py --group all")
    input_hashes = verify_restored_inputs(data)

    cache, meta_path = work / "wormdense_features.npy", work / "wormdense_features.json"
    if not (cache.is_file() and meta_path.is_file()):
        raise SystemExit("H31b feature cache missing; run scripts/build_h31b_features.py first")
    w_meta = json.loads(meta_path.read_text())
    if w_meta.get("code_revision") not in (revision, None) and w_meta.get("code_revision") != "unknown":
        # a cache built from different frozen code must be rebuilt so the screen sees exactly the
        # committed feature builder; accept only same-revision or unknown (pre-revision) caches
        raise SystemExit(f"H31b cache built at revision {w_meta.get('code_revision')}, not {revision}; rebuild it")
    features = np.load(cache)
    if list(w_meta.get("names", [])) != W_NAMES:
        raise SystemExit("H31b cache name manifest does not match the frozen W_NAMES")
    if features.shape[0] != len(W_NAMES):
        raise SystemExit(f"H31b cache shape {features.shape} does not match ({len(W_NAMES)}, n_foot)")
    frozen_inputs = dict(frozen_inputs, cache_sha256=sha256_file(cache), cache_names=W_NAMES)

    ctx = load_context(work)
    ctx.h31_features = features
    ctx.h31_names = list(W_NAMES)
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)
    n_base = ctx.static.shape[0] + len(ctx.e_names) + len(ctx.extra_names) + len(ctx.h27_names)
    assert n_base == 81, f"expected the 81-column H34 control layout, found {n_base}"

    prereg_sha = sha256_file(PREREG_PATH)
    design = dict(
        experiment="H31b dense continuous worming persistence screen",
        stage=stage,
        preregistration=str(PREREG_PATH.relative_to(ROOT)),
        preregistration_sha256=prereg_sha,
        protocol="paired, one fit per arm per (fold, draw); arms differ only in appended W columns",
        folds=[FOLDS[f] for f in sorted(FOLDS)],
        draws=draws,
        draw_seed_inventory={
            "used_before": "0-13 (factorial/addons/H27/H28/H30/H31), 14/15 (factorial confirmation), 20/21 (H34)",
            "this_stage": draws,
        },
        arms=list(ARMS),
        primary=PRIMARY,
        gates=GATES,
        constants=dict(k_frac=KFRAC, dot_min_dist_px=DOT_MIN_DIST, hgb=HGB_PARAMS),
        git=dict(branch=branch, revision=revision),
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         packages={n: package_version(n) for n in ("rasterio", "scikit-learn", "scipy", "numpy")}),
        inputs=input_hashes,
        frozen_inputs=frozen_inputs,
    )
    out.mkdir(parents=True, exist_ok=True)
    design_path.write_text(json.dumps(design, indent=2) + "\n")
    print(f"H31b {stage}: draws {draws}, folds {list(FOLDS)}; base {n_base} columns + W {len(W_NAMES)}; "
          f"SGMC off-catalogue truth {sgmc_stats['off_catalogue']:,} px", flush=True)

    rows: list[dict] = []
    t_start = time.time()
    with cells_path.open("w", encoding="utf-8") as sink:
        for fold in sorted(FOLDS):
            for seed in draws:
                t0 = time.time()
                cell = Cell(ctx, fold, seed, extras=True, h27=True, h31=True)
                base_cols = list(range(n_base))
                w_idx = {b: [n_base + 4 * i + j for j in range(4)] for i, b in enumerate(("RTP", "PSG", "GRAV"))}
                arm_cols = {
                    "C_base": base_cols,
                    "C_wrtp": base_cols + w_idx["RTP"],
                    "C_wpsg": base_cols + w_idx["PSG"],
                    "C_wgrav": base_cols + w_idx["GRAV"],
                    "C_wall": base_cols + [n_base + j for j in range(12)],
                }
                for arm in ARMS:
                    probabilities, timing = cell.fit_predict(arm_cols[arm], seed=seed)
                    emitted, topk = cell.emit(probabilities, dotted=True, min_dist=DOT_MIN_DIST)
                    result = cell.evaluate(emitted)
                    sl = cell.sl
                    sg = dti_binary(emitted, sgmc_truth[sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                    row = dict(
                        fold=fold, fold_name=FOLDS[fold], draw=seed, arm=arm,
                        n_cols=len(arm_cols[arm]), **result,
                        sgmc_dti=float(sg["dti"]), sgmc_coverage=float(sg["coverage"]),
                        sgmc_n_truth=int(sg["n_truth"]),
                        fit_s=float(timing["fit_s"]), predict_s=float(timing["predict_s"]),
                    )
                    rows.append(row)
                    sink.write(json.dumps(row) + "\n")
                    sink.flush()
                summary = " ".join(
                    f"{a.split('_')[0] if a != 'C_base' else 'base'}="
                    + f"{next(r['dti'] for r in rows if r['fold'] == fold and r['draw'] == seed and r['arm'] == a):.4f}"
                    for a in ARMS
                )
                print(f"fold={FOLDS[fold]} draw={seed} {summary}  ({time.time() - t0:.0f}s)", flush=True)

    def mean_dti(arm: str, draw: int) -> float:
        vals = [r["dti"] for r in rows if r["draw"] == draw and r["arm"] == arm]
        return float(np.mean(vals)) if vals else float("nan")

    def delta(arm: str, draw: int, fold: int) -> float:
        vals_p = [r["dti"] for r in rows if r["draw"] == draw and r["fold"] == fold and r["arm"] == arm]
        vals_c = [r["dti"] for r in rows if r["draw"] == draw and r["fold"] == fold and r["arm"] == "C_base"]
        if not vals_p or not vals_c:
            return float("nan")
        return float(vals_p[0] - vals_c[0])

    per_draw = {}
    for draw in draws:
        ds = [delta(PRIMARY, draw, fold) for fold in sorted(FOLDS)]
        per_draw[draw] = dict(
            per_fold={FOLDS[f]: delta(PRIMARY, draw, f) for f in sorted(FOLDS)},
            mean=float(np.mean(ds)),
            positive_folds=int(sum(1 for d in ds if d > 0)),
            min_fold=float(np.min(ds)),
        )
    mean_w8 = float(np.mean([r["dti"] for r in rows if r["arm"] == PRIMARY]))
    gates = dict(
        per_draw=per_draw,
        mean_wall_8cell=mean_w8,
        all_cells_present=bool(len(rows) == len(sorted(FOLDS)) * len(draws) * len(ARMS)),
        all_finite=bool(all(np.isfinite(r["dti"]) for r in rows)),
    )
    g1 = all(per_draw[d]["mean"] >= GATES["min_mean_gain_per_draw"] for d in draws)
    g2 = all(per_draw[d]["positive_folds"] >= GATES["min_positive_folds_per_draw"] for d in draws)
    g3 = all(per_draw[d]["min_fold"] >= GATES["max_fold_loss"] for d in draws)
    g4 = mean_w8 > GATES["holdout_best"]
    g5 = gates["all_cells_present"] and gates["all_finite"]
    arms_mean = {a: float(np.mean([r["dti"] for r in rows if r["arm"] == a])) for a in ARMS}
    sgmc_mean = {a: float(np.mean([r["sgmc_dti"] for r in rows if r["arm"] == a])) for a in ARMS}
    summary = dict(
        experiment="H31b dense continuous worming persistence",
        stage=stage,
        elapsed_s=time.time() - t_start,
        arms=arms_mean,
        sgmc_arms=sgmc_mean,
        paired_per_draw=per_draw,
        gates=gates,
        gate_checks=dict(G1_mean_gain_per_draw=g1, G2_positive_folds_per_draw=g2,
                         G3_fold_floor=g3, G4_beats_holdout_best=g4, G5_cells_and_manifest=g5),
        sgmc_stats=sgmc_stats,
        pass_fail="PASS" if all((g1, g2, g3, g4, g5)) else "FAIL",
        interpretation=(
            "Proxy outcome only: exact masked DTI on hidden catalogue components plus a secondary "
            "state-geologic-map off-catalogue class (descriptive; the two proxies are in a registered "
            "conflict). Neither is the organizer's hidden expert label set and neither is a "
            "competition score. A PASS authorizes a reviewed full-data build and an owner decision, "
            "not an automatic submission."
        ),
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("arms", "sgmc_arms", "paired_per_draw", "gates", "gate_checks", "pass_fail")}, indent=2))
    if stage == "screen" and summary["pass_fail"] == "PASS":
        print("screen PASS: fresh confirmation on draws 24/25 is authorized (--stage confirm).")
    elif stage == "confirm" and summary["pass_fail"] == "PASS":
        print("confirmation PASS: a reviewed full-data candidate build + exact-file audit is authorized; owner decides slot use.")
    else:
        print("FAIL: no candidate file, no slot, per the frozen decision rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
