#!/usr/bin/env python3
"""Run the frozen H31 paired spatial screen or fresh confirmation; never contacts DrivenData."""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.experiment import Cell, HGB_PARAMS, N_NEG, load_context  # noqa: E402
from gemsdoe.h30 import H30_BASE_EXTRAS  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.submission import sha256_file  # noqa: E402
from gemsdoe.thinning import score_ordered_dots  # noqa: E402
from gemsdoe.worms import H31_NAMES  # noqa: E402
from scripts.analyze_h31_worming import verify_passing_screen  # noqa: E402

DRAWS = {"screen": [10, 11], "confirm": [12, 13]}
FOLDS = ["NW", "NE", "SW", "SE"]
DESIGN_SEED = 20261005
BASE_FAMILIES = "BDE"
KFRAC = 0.0245
MIN_DIST_PX = 2.4
PREREG_PATH = ROOT / "knowledge" / "02_preregistered_h31_worming_2026-10-03.md"
H31_CACHE = "h31_potential_persistence.npy"
FROZEN_CODE_PATHS = [
    "src/gemsdoe",
    "scripts",
    "tests",
    "knowledge/01_candidates_ranked_2026-10-03.md",
    "knowledge/02_preregistered_h31_worming_2026-10-03.md",
    "registry/data_manifest.json",
    "registry/hypotheses.json",
    "pyproject.toml",
    "requirements.txt",
]


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


ARENA_BRANCH_RE = re.compile(r"^arena/[0-9a-f]{8}-gemsdoe29$")


def require_clean_fixed_branch() -> tuple[str, str]:
    """Refuse to fit outside an Arena session branch of this repository, with a clean committed tree.

    The earlier revision of this guard hard-coded the first session's branch name; that pinned the
    frozen protocol to one ephemeral branch id. The guard now accepts any Arena session branch of this
    repository (the preregistration is frozen by hash, the source by commit) and the design records the
    actual branch name that was used.
    """
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"cannot record frozen Git state: {exc}") from exc
    if not ARENA_BRANCH_RE.match(branch):
        raise SystemExit(f"refusing to fit outside an Arena session branch of this repository; found {branch!r}")
    if status.strip():
        raise SystemExit("refusing to fit with a dirty worktree; freeze the preregistration, code, and tests first")
    return branch, revision


def frozen_source_revision(current_revision: str, stage: str) -> str:
    """Keep screen/confirmation on identical committed source even when evidence commits advance HEAD."""
    if stage == "screen":
        return current_revision
    screen_design = ROOT / "evidence" / "h31_worm_screen" / "design.json"
    if not screen_design.is_file():
        raise SystemExit("screen design.json is missing; confirmation cannot identify the frozen source commit")
    design = json.loads(screen_design.read_text())
    frozen = design.get("code_revision")
    if not isinstance(frozen, str) or len(frozen) != 40 or any(ch not in "0123456789abcdef" for ch in frozen):
        raise SystemExit("screen design has an invalid frozen code revision")
    try:
        subprocess.run(["git", "cat-file", "-e", f"{frozen}^{{commit}}"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "merge-base", "--is-ancestor", frozen, current_revision], cwd=ROOT, check=True)
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", f"{frozen}..{current_revision}", "--", *FROZEN_CODE_PATHS],
            cwd=ROOT,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"cannot verify unchanged H31 source between screen and confirmation: {exc}") from exc
    if changed.strip():
        raise SystemExit("H31 source/preregistration changed after screen; confirmation is blocked")
    return frozen


def verify_restored_inputs(data: Path) -> dict[str, dict[str, str | int]]:
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    receipt_path = data / "restore_receipt.json"
    if not receipt_path.is_file():
        raise SystemExit("missing restore_receipt.json; run scripts/restore_h31_data.py --group all first")
    receipt = json.loads(receipt_path.read_text())
    by_id = {row.get("id"): row for row in receipt if isinstance(row, dict)}
    verified: dict[str, dict[str, str | int]] = {}
    for row in manifest["files"]:
        path = data / row["dest"]
        if not path.is_file():
            raise SystemExit(f"missing required hash-pinned input: {path}")
        if path.stat().st_size != row["bytes"]:
            raise SystemExit(f"byte-size mismatch for {row['id']}: {path.stat().st_size} != {row['bytes']}")
        digest = sha256_file(path)
        if digest != row["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {row['id']}: {digest} != {row['sha256']}")
        logged = by_id.get(row["id"])
        if not isinstance(logged, dict) or logged.get("sha256") != digest:
            raise SystemExit(f"restore receipt does not attest the verified bytes for {row['id']}")
        verified[row["id"]] = {"sha256": digest, "bytes": path.stat().st_size}
    return verified


def cache_records(work: Path, expected_code_revision: str) -> dict[str, dict[str, str | int]]:
    required = [
        "static_ABCD.npy",
        "static_ABCD.npy.names.json",
        "addons.npy",
        "addons.npy.names.json",
        "bands/_footprint.npy",
        "bands/_labels.npy",
        "bands/02_rtp.npy",
        "bands/13_iso_grav_anom.npy",
        H31_CACHE,
        H31_CACHE + ".names.json",
        H31_CACHE + ".metadata.json",
    ]
    records = {}
    for name in required:
        path = work / name
        if not path.is_file():
            raise SystemExit(f"missing derived input/cache: {path}; run the documented build scripts first")
        records[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    meta = json.loads((work / (H31_CACHE + ".metadata.json")).read_text())
    if meta.get("output", {}).get("sha256") != records[H31_CACHE]["sha256"]:
        raise SystemExit("H31 metadata output checksum does not match its cache")
    if meta.get("preregistration_sha256") != sha256_file(PREREG_PATH):
        raise SystemExit("H31 feature cache was built against a different preregistration")
    if meta.get("code_revision") != expected_code_revision or meta.get("dirty_worktree_at_cache_build") is not False:
        raise SystemExit("H31 cache was not built from the frozen clean source revision")
    expected_inputs = {
        "rtp": "bands/02_rtp.npy",
        "iso_grav_anom": "bands/13_iso_grav_anom.npy",
        "footprint": "bands/_footprint.npy",
    }
    for name, cache_name in expected_inputs.items():
        input_record = meta.get("input_arrays", {}).get(name, {})
        cache_record = records[cache_name]
        if input_record.get("sha256") != cache_record["sha256"] or input_record.get("bytes") != cache_record["bytes"]:
            raise SystemExit(f"H31 feature metadata input hash/size mismatch: {name}")
    diagnostics = meta.get("diagnostics", {}).get("config", {})
    expected_config = {
        "cell_size_m": 100.0,
        "height_sequence_m": [0, 100, 200, 400, 800, 1200],
        "taper_px": 64,
        "pad_px": 128,
        "boundary_guard_px": 16,
        "edge_percentile": 90.0,
        "max_match_px": 2.0,
    }
    if any(diagnostics.get(name) != value for name, value in expected_config.items()):
        raise SystemExit("H31 feature-cache configuration differs from the frozen preregistration")
    names = json.loads((work / (H31_CACHE + ".names.json")).read_text())
    if names != H31_NAMES or meta.get("output", {}).get("feature_names") != H31_NAMES:
        raise SystemExit("H31 feature names differ from the frozen list")
    if meta.get("output", {}).get("dtype") != "float32":
        raise SystemExit("H31 feature cache dtype differs from the frozen float32 design")
    return records


def canonical_arms() -> list[dict]:
    return [
        {"arm": "BASE_NO_TIP", "PSG": -1, "GRAV": -1},
        {"arm": "T_BASE", "PSG": -1, "GRAV": -1},
        {"arm": "T_PLUS_PSG", "PSG": 1, "GRAV": -1},
        {"arm": "T_PLUS_GRAV", "PSG": -1, "GRAV": 1},
        {"arm": "T_PLUS_PSG_GRAV", "PSG": 1, "GRAV": 1},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=tuple(DRAWS), default="screen")
    parser.add_argument("--out", default=None, help="new run directory; refuses to overwrite nonempty evidence")
    args = parser.parse_args()

    execution_branch, execution_revision = require_clean_fixed_branch()
    prereg_sha = sha256_file(PREREG_PATH)
    if args.stage == "confirm":
        verify_passing_screen(ROOT / "evidence" / "h31_worm_screen")
    revision = frozen_source_revision(execution_revision, args.stage)

    out = Path(args.out) if args.out else ROOT / "evidence" / f"h31_worm_{args.stage}"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise SystemExit(f"refusing to overwrite nonempty H31 evidence: {out}; choose a fresh path")
    out.mkdir(parents=True, exist_ok=True)

    data = data_dir()
    work = work_dir()
    data_hashes = verify_restored_inputs(data)
    cache_hashes = cache_records(work, revision)
    ctx = load_context(work)
    if ctx.addon is None or ctx.addon.shape != (5, ctx.fi.size):
        raise SystemExit("add-on cache is missing or malformed; run scripts/build_addons.py first")
    ctx.h31_features = np.load(work / H31_CACHE, mmap_mode="r")
    ctx.h31_names = json.loads((work / (H31_CACHE + ".names.json")).read_text())
    if ctx.h31_features.shape != (len(H31_NAMES), ctx.fi.size):
        raise SystemExit(f"H31 feature cache shape mismatch: {ctx.h31_features.shape}")
    if not np.isfinite(ctx.h31_features).all():
        raise SystemExit("H31 feature cache contains nonfinite values")
    if (np.asarray(ctx.h31_features) < 0).any() or (np.asarray(ctx.h31_features) > 1).any():
        raise SystemExit("H31 feature values must lie in [0,1]")

    canonical = canonical_arms()
    row_order = np.random.default_rng(DESIGN_SEED).permutation(len(canonical)).tolist()
    randomized = [canonical[i] for i in row_order]
    base_cols = ctx.columns(BASE_FAMILIES) + ctx.named(H30_BASE_EXTRAS)
    tip_cols = ctx.named(["H27_tip"])
    h31_start = ctx.static.shape[0] + len(ctx.e_names) + len(ctx.extra_names) + 3
    psg_cols = [h31_start, h31_start + 1]
    grav_cols = [h31_start + 2, h31_start + 3]
    joint_cols = [h31_start + 4]
    arm_cols = {
        "BASE_NO_TIP": base_cols,
        "T_BASE": base_cols + tip_cols,
        "T_PLUS_PSG": base_cols + tip_cols + psg_cols,
        "T_PLUS_GRAV": base_cols + tip_cols + grav_cols,
        "T_PLUS_PSG_GRAV": base_cols + tip_cols + psg_cols + grav_cols + joint_cols,
    }
    if any(max(cols) >= ctx.static.shape[0] + len(ctx.e_names) + len(ctx.extra_names) + 3 + len(H31_NAMES) for cols in arm_cols.values()):
        raise SystemExit("feature-column indices exceed the constructed H31 cell matrix")

    design = {
        "schema_version": 1,
        "hypothesis": "H31 multiscale potential-field edge persistence (worming-like proxy)",
        "stage": args.stage,
        "preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": prereg_sha,
        "code_revision": revision,
        "execution_revision": execution_revision,
        "branch": execution_branch,
        "clean_worktree_before_fit": True,
        "draws": DRAWS[args.stage],
        "spatial_folds": FOLDS,
        "design_seed": DESIGN_SEED,
        "canonical_matrix": canonical,
        "row_order_zero_based": row_order,
        "randomized_matrix": randomized,
        "factorial_arms": ["T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV", "T_PLUS_PSG_GRAV"],
        "primary_candidate": "T_PLUS_PSG_GRAV",
        "registered_controls": ["BASE_NO_TIP", "T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV"],
        "feature_families": BASE_FAMILIES,
        "fixed_addons": H30_BASE_EXTRAS,
        "fixed_tip_control": "H27_tip",
        "feature_names": H31_NAMES,
        "feature_columns": {
            "base": base_cols,
            "tip": tip_cols,
            "psg": psg_cols,
            "gravity": grav_cols,
            "joint": joint_cols,
        },
        "model": {
            "class": "sklearn.ensemble.HistGradientBoostingClassifier",
            "parameters": {
                "max_iter": HGB_PARAMS["max_iter"],
                "learning_rate": HGB_PARAMS["learning_rate"],
                "max_leaf_nodes": HGB_PARAMS["max_leaf_nodes"],
                "min_samples_leaf": HGB_PARAMS["min_samples_leaf"],
                "l2_regularization": HGB_PARAMS["l2_regularization"],
                "class_weight": {str(key): value for key, value in HGB_PARAMS["class_weight"].items()},
                "early_stopping": HGB_PARAMS["early_stopping"],
                "random_state": "draw_seed",
                "negative_sample_count_max": N_NEG,
            },
        },
        "holdout": {
            "hide_fraction": 0.20,
            "quadrants": FOLDS,
            "collar_px": 15,
            "domain_erosion_px": 12,
            "visible_catalogue_only": True,
            "same_cell_masks_and_training_samples_across_arms": True,
        },
        "emission": {
            "method": "Hessian ridge NMS -> drop visible known faults -> top-K -> score-ordered Poisson disk",
            "nms_sigma_px": 1.0,
            "k_fraction_of_scored_domain": KFRAC,
            "min_distance_px": MIN_DIST_PX,
        },
        "promotion_gate": {
            "mean_paired_gain_over_best_same_run_control": "> +0.001",
            "positive_spatial_blocks": ">= 3 of 4",
            "worst_spatial_block_gain": ">= -0.010",
            "catalogue_hug_share_increase": "<= +0.10",
            "fresh_confirmation_required": True,
        },
        "data_manifest_sha256_and_bytes": data_hashes,
        "work_cache_sha256_and_bytes": cache_hashes,
        "h31_feature_build_metadata_sha256": sha256_file(work / (H31_CACHE + ".metadata.json")),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": package_version("numpy"),
            "scipy": package_version("scipy"),
            "scikit-learn": package_version("scikit-learn"),
            "rasterio": package_version("rasterio"),
        },
        "notes": (
            "All arms in each fold/draw share one Cell, one visible catalogue, one training sample, and one scorer. "
            "The holdout is a catalogue-gap proxy computed from owner-mirror data, not official hidden-fault truth. "
            "No live leaderboard or submission endpoint is contacted."
        ),
    }
    design_path = out / "design.json"
    cells_path = out / "cells.jsonl"
    if design_path.exists() or cells_path.exists():
        raise SystemExit("refusing to overwrite an existing design.json or cells.jsonl")
    design_path.write_text(json.dumps(design, indent=2) + "\n")

    start = time.time()
    with cells_path.open("w", encoding="utf-8") as sink:
        for fold in range(4):
            for draw_seed in DRAWS[args.stage]:
                cell = Cell(ctx, fold, draw_seed, extras=True, h27=True, h31=True)
                k = int(round(KFRAC * cell.dom_c.sum()))
                for run_order, config in enumerate(randomized, start=1):
                    arm = config["arm"]
                    probabilities, timing = cell.fit_predict(arm_cols[arm], seed=draw_seed)
                    score_crop, candidates = cell.candidates(probabilities, k)
                    emitted = score_ordered_dots(score_crop, candidates, MIN_DIST_PX)
                    row = {
                        "stage": args.stage,
                        "fold": fold,
                        "fold_name": FOLDS[fold],
                        "draw": draw_seed,
                        "run_order": run_order,
                        "arm": arm,
                        "PSG": config["PSG"],
                        "GRAV": config["GRAV"],
                        "design_seed": DESIGN_SEED,
                        "k_fraction": KFRAC,
                        "min_distance_px": MIN_DIST_PX,
                        "auc": cell.auc(probabilities),
                        **cell.evaluate(emitted),
                        **timing,
                    }
                    sink.write(json.dumps(row, allow_nan=False) + "\n")
                    sink.flush()
                    print(
                        f"[{args.stage} {FOLDS[fold]} draw={draw_seed} {run_order}/5 {arm}] "
                        f"DTI={row['dti']:.6f} emitted={row['emitted']:,} "
                        f"fit={row['fit_s']:.1f}s elapsed={time.time() - start:.0f}s",
                        flush=True,
                    )
                del cell
    print(f"DONE: {cells_path}", flush=True)


if __name__ == "__main__":
    main()
