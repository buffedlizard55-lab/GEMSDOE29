#!/usr/bin/env python3
"""Validate/analyze H31 raw cells and recompute the paired spatial promotion gate."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.experiment import HGB_PARAMS, N_NEG  # noqa: E402
from gemsdoe.h30 import H30_BASE_EXTRAS  # noqa: E402
from gemsdoe.metric import ALPHA, BETA, EPS  # noqa: E402
from gemsdoe.submission import sha256_file  # noqa: E402
from gemsdoe.worms import H31_NAMES  # noqa: E402

EXPECTED_DRAWS = {"screen": [10, 11], "confirm": [12, 13]}
FOLDS = ["NW", "NE", "SW", "SE"]
ARMS = ["BASE_NO_TIP", "T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV", "T_PLUS_PSG_GRAV"]
CANDIDATE = "T_PLUS_PSG_GRAV"
H31_CACHE = "h31_potential_persistence.npy"
CACHE_RECORD_NAMES = [
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
DESIGN_SEED = 20261005
CANONICAL_MATRIX = [
    {"arm": "BASE_NO_TIP", "PSG": -1, "GRAV": -1},
    {"arm": "T_BASE", "PSG": -1, "GRAV": -1},
    {"arm": "T_PLUS_PSG", "PSG": 1, "GRAV": -1},
    {"arm": "T_PLUS_GRAV", "PSG": -1, "GRAV": 1},
    {"arm": "T_PLUS_PSG_GRAV", "PSG": 1, "GRAV": 1},
]
PREREG = ROOT / "knowledge" / "02_preregistered_h31_worming_2026-10-03.md"


def _is_hex(value: str) -> bool:
    return all(character in "0123456789abcdef" for character in value.lower())


def _numeric(row: dict[str, Any], key: str, *, low: float | None = None, high: float | None = None) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"raw cell field {key!r} must be finite numeric")
    out = float(value)
    if low is not None and out < low:
        raise ValueError(f"raw cell field {key!r} is below {low}")
    if high is not None and out > high:
        raise ValueError(f"raw cell field {key!r} is above {high}")
    return out


def _validate_design(design: dict[str, Any], stage: str) -> list[str]:
    """Check design.json against the checked-in fixed protocol, not just its own claims."""
    if not isinstance(design, dict):
        raise ValueError("design.json must be a JSON object")
    if design.get("stage") != stage or design.get("draws") != EXPECTED_DRAWS[stage]:
        raise ValueError(f"design stage/draws differ from frozen {stage} draws {EXPECTED_DRAWS[stage]}")
    if design.get("spatial_folds") != FOLDS:
        raise ValueError("design spatial folds differ from the frozen NW/NE/SW/SE order")
    if design.get("preregistration") != str(PREREG.relative_to(ROOT)):
        raise ValueError("design points to an unexpected preregistration")
    if design.get("preregistration_sha256") != sha256_file(PREREG):
        raise ValueError("design preregistration hash does not match the current frozen register")
    if design.get("primary_candidate") != CANDIDATE or design.get("feature_names") != H31_NAMES:
        raise ValueError("design candidate/feature names differ from the frozen H31 protocol")
    if design.get("feature_families") != "BDE" or design.get("fixed_addons") != H30_BASE_EXTRAS:
        raise ValueError("design baseline feature families or add-ons differ from preregistration")
    branch = design.get("branch")
    if not isinstance(branch, str) or not re.match(r"^arena/[0-9a-f]{8}-gemsdoe29$", branch):
        raise ValueError("design must attest a clean fit on an Arena session branch of this repository")
    if design.get("clean_worktree_before_fit") is not True:
        raise ValueError("design must attest a clean worktree before fitting")
    for revision_name in ("code_revision", "execution_revision"):
        revision = design.get(revision_name)
        if not isinstance(revision, str) or len(revision) != 40 or not _is_hex(revision):
            raise ValueError(f"design {revision_name} must be a 40-character Git revision")
    if stage == "screen" and design["code_revision"] != design["execution_revision"]:
        raise ValueError("screen must use the clean frozen source commit as its execution commit")
    if design.get("design_seed") != DESIGN_SEED or design.get("canonical_matrix") != CANONICAL_MATRIX:
        raise ValueError("design seed or canonical five-arm matrix differs from the frozen protocol")

    order = np.random.default_rng(DESIGN_SEED).permutation(len(CANONICAL_MATRIX)).tolist()
    randomized = [CANONICAL_MATRIX[index] for index in order]
    if design.get("row_order_zero_based") != order or design.get("randomized_matrix") != randomized:
        raise ValueError("randomized matrix/order is not the deterministic registered permutation")
    if design.get("factorial_arms") != ["T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV", "T_PLUS_PSG_GRAV"]:
        raise ValueError("design factorial arms differ from the frozen four-arm contrast")
    if design.get("registered_controls") != ["BASE_NO_TIP", "T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV"]:
        raise ValueError("design controls differ from the frozen same-run comparison")
    if design.get("fixed_tip_control") != "H27_tip":
        raise ValueError("design fixed tip control differs from preregistration")

    expected_model = {
        "max_iter": HGB_PARAMS["max_iter"],
        "learning_rate": HGB_PARAMS["learning_rate"],
        "max_leaf_nodes": HGB_PARAMS["max_leaf_nodes"],
        "min_samples_leaf": HGB_PARAMS["min_samples_leaf"],
        "l2_regularization": HGB_PARAMS["l2_regularization"],
        "class_weight": {str(key): value for key, value in HGB_PARAMS["class_weight"].items()},
        "early_stopping": HGB_PARAMS["early_stopping"],
        "random_state": "draw_seed",
        "negative_sample_count_max": N_NEG,
    }
    model = design.get("model", {})
    if model.get("class") != "sklearn.ensemble.HistGradientBoostingClassifier" or model.get("parameters") != expected_model:
        raise ValueError("design model class/parameters differ from the frozen settings")
    expected_holdout = {
        "hide_fraction": 0.20,
        "quadrants": FOLDS,
        "collar_px": 15,
        "domain_erosion_px": 12,
        "visible_catalogue_only": True,
        "same_cell_masks_and_training_samples_across_arms": True,
    }
    if design.get("holdout") != expected_holdout:
        raise ValueError("design holdout settings differ from preregistration")
    expected_emission = {
        "method": "Hessian ridge NMS -> drop visible known faults -> top-K -> score-ordered Poisson disk",
        "nms_sigma_px": 1.0,
        "k_fraction_of_scored_domain": 0.0245,
        "min_distance_px": 2.4,
    }
    if design.get("emission") != expected_emission:
        raise ValueError("design emission settings differ from preregistration")
    expected_gate = {
        "mean_paired_gain_over_best_same_run_control": "> +0.001",
        "positive_spatial_blocks": ">= 3 of 4",
        "worst_spatial_block_gain": ">= -0.010",
        "catalogue_hug_share_increase": "<= +0.10",
        "fresh_confirmation_required": True,
    }
    if design.get("promotion_gate") != expected_gate:
        raise ValueError("design promotion gate differs from preregistration")

    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    input_records = design.get("data_manifest_sha256_and_bytes", {})
    if not isinstance(input_records, dict) or set(input_records) != {item["id"] for item in manifest["files"]}:
        raise ValueError("design does not record every hash-pinned input in the data manifest")
    for item in manifest["files"]:
        record = input_records.get(item["id"], {})
        if not isinstance(record, dict) or record.get("sha256") != item["sha256"] or record.get("bytes") != item["bytes"]:
            raise ValueError(f"design restored-input provenance differs from manifest for {item['id']}")
    cache_records = design.get("work_cache_sha256_and_bytes", {})
    if not isinstance(cache_records, dict) or set(cache_records) != set(CACHE_RECORD_NAMES) or any(
        not isinstance(record, dict)
        or not isinstance(record.get("sha256"), str)
        or len(record["sha256"]) != 64
        or not _is_hex(record["sha256"])
        or isinstance(record.get("bytes"), bool)
        or not isinstance(record.get("bytes"), int)
        or record["bytes"] <= 0
        for record in cache_records.values()
    ):
        raise ValueError("design work-cache provenance is missing or malformed")
    return [row["arm"] for row in randomized]


def _load_and_validate(run_dir: Path, stage: str) -> tuple[dict, list[dict], dict]:
    if stage not in EXPECTED_DRAWS:
        raise ValueError(f"unknown H31 stage {stage!r}")
    design_path = run_dir / "design.json"
    cells_path = run_dir / "cells.jsonl"
    if not design_path.is_file() or not cells_path.is_file():
        raise ValueError("run directory must contain design.json and cells.jsonl")
    design = json.loads(design_path.read_text())
    expected_order = _validate_design(design, stage)

    rows = []
    for line_number, line in enumerate(cells_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at cells.jsonl line {line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"cells.jsonl line {line_number} is not an object")
        rows.append(row)

    expected_keys = {
        (fold, draw, arm)
        for fold in range(4)
        for draw in EXPECTED_DRAWS[stage]
        for arm in ARMS
    }
    lookup: dict[tuple[int, int, str], dict] = {}
    order_by_cell: dict[tuple[int, int], list[str]] = {}
    for row in rows:
        fold = row.get("fold")
        draw = row.get("draw")
        arm = row.get("arm")
        run_order = row.get("run_order")
        if isinstance(fold, bool) or not isinstance(fold, int) or fold not in range(4):
            raise ValueError("raw cell fold must be an integer from 0 to 3")
        if isinstance(draw, bool) or not isinstance(draw, int) or draw not in EXPECTED_DRAWS[stage]:
            raise ValueError(f"raw cell draw is not a registered integer for {stage}")
        if arm not in ARMS:
            raise ValueError(f"unregistered arm in raw cells: {arm!r}")
        if row.get("stage") != stage or row.get("fold_name") != FOLDS[fold]:
            raise ValueError("raw cell stage/fold name differs from the frozen design")
        if row.get("design_seed") != design.get("design_seed"):
            raise ValueError("raw cell randomized-design seed differs from design.json")
        if isinstance(run_order, bool) or not isinstance(run_order, int) or run_order not in range(1, 6):
            raise ValueError("raw cell run_order must be an integer from 1 to 5")
        if run_order != expected_order.index(arm) + 1:
            raise ValueError("raw cell run_order differs from the deterministic arm randomization")
        factor_values = {item["arm"]: (item["PSG"], item["GRAV"]) for item in CANONICAL_MATRIX}
        if any(isinstance(row.get(name), bool) or not isinstance(row.get(name), int) for name in ("PSG", "GRAV")):
            raise ValueError("raw cell factorial indicators must be integer -1/1 values")
        if (row.get("PSG"), row.get("GRAV")) != factor_values[arm]:
            raise ValueError("raw cell factorial indicators differ from the registered arm matrix")
        key = (fold, int(draw), arm)
        if key in lookup:
            raise ValueError(f"duplicate raw cell key: {key}")
        for name in ("dti", "hug", "coverage", "auc", "fit_s", "predict_s"):
            _numeric(row, name, low=0.0 if name in {"dti", "hug", "coverage", "auc", "fit_s", "predict_s"} else None,
                     high=1.0 if name in {"dti", "hug", "coverage", "auc"} else None)
        for name in ("emitted", "n_truth"):
            value = row.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"raw cell field {name!r} must be a nonnegative integer")
        tp, fp = _numeric(row, "tp", low=0.0), _numeric(row, "fp", low=0.0)
        n_truth = row["n_truth"]
        if n_truth <= 0 or tp > n_truth + 1e-9:
            raise ValueError("raw cell truth count must be positive and weighted true positives cannot exceed it")
        expected_coverage = tp / n_truth
        expected_dti = tp / (tp + ALPHA * fp + BETA * (n_truth - tp) + EPS)
        if not math.isclose(_numeric(row, "coverage", low=0.0, high=1.0), expected_coverage, rel_tol=0.0, abs_tol=1e-10):
            raise ValueError("raw cell coverage is inconsistent with TP and hidden-truth count")
        if not math.isclose(_numeric(row, "dti", low=0.0, high=1.0), expected_dti, rel_tol=0.0, abs_tol=1e-10):
            raise ValueError("raw cell DTI is inconsistent with TP, FP and hidden-truth count")
        if row.get("k_fraction") != 0.0245 or row.get("min_distance_px") != 2.4:
            raise ValueError("raw cell emission settings differ from preregistration")
        lookup[key] = row
        order_by_cell.setdefault((fold, int(draw)), []).append(arm)
    if set(lookup) != expected_keys:
        missing, extra = expected_keys - set(lookup), set(lookup) - expected_keys
        raise ValueError(f"incomplete/unexpected H31 cells; missing={sorted(missing)}, extra={sorted(extra)}")
    for key, observed in order_by_cell.items():
        if observed != expected_order:
            raise ValueError(f"row order differs from frozen randomization in cell {key}: {observed}")
    if len(rows) != 40:
        raise ValueError(f"expected 40 complete cells, found {len(rows)}")

    hashes = {
        "design_sha256": sha256_file(design_path),
        "cells_sha256": sha256_file(cells_path),
        "design_bytes": design_path.stat().st_size,
        "cells_bytes": cells_path.stat().st_size,
    }
    return design, rows, {"lookup": lookup, "hashes": hashes}


def _mean(rows: list[dict], fold: int, draws: list[int], arm: str, metric: str) -> float:
    return float(np.mean([rows[(fold, draw, arm)][metric] for draw in draws]))


def _effect_summary(values: list[float]) -> dict[str, Any]:
    x = np.asarray(values, dtype=float)
    mean = float(x.mean())
    if x.size < 2:
        lo = hi = mean
    else:
        half = float(student_t.ppf(0.975, x.size - 1) * x.std(ddof=1) / np.sqrt(x.size))
        lo, hi = mean - half, mean + half
    return {
        "mean_across_four_spatial_blocks": mean,
        "descriptive_95pct_t_interval": [float(lo), float(hi)],
        "per_spatial_block": [float(v) for v in x],
        "effective_spatial_blocks": int(x.size),
        "interpretation": "descriptive only; four spatial blocks are too few for a strong population-level claim",
    }


def analyze_run(run_dir: Path, stage: str) -> dict[str, Any]:
    design, rows, internal = _load_and_validate(run_dir, stage)
    lookup = internal["lookup"]
    draws = EXPECTED_DRAWS[stage]

    fold_dti: dict[str, list[float]] = {arm: [] for arm in ARMS}
    fold_hug: dict[str, list[float]] = {arm: [] for arm in ARMS}
    paired_gain: list[float] = []
    paired_hug_delta: list[float] = []
    chosen_control: list[str] = []
    for fold in range(4):
        for arm in ARMS:
            fold_dti[arm].append(_mean(lookup, fold, draws, arm, "dti"))
            fold_hug[arm].append(_mean(lookup, fold, draws, arm, "hug"))
        controls = [arm for arm in ARMS if arm != CANDIDATE]
        best = max(controls, key=lambda arm: fold_dti[arm][fold])
        chosen_control.append(best)
        paired_gain.append(fold_dti[CANDIDATE][fold] - fold_dti[best][fold])
        paired_hug_delta.append(fold_hug[CANDIDATE][fold] - fold_hug[best][fold])

    mean_gain = float(np.mean(paired_gain))
    gate = {
        "mean_gain_gt_0_001": bool(mean_gain > 0.001),
        "positive_in_at_least_3_of_4_blocks": bool(sum(v > 0 for v in paired_gain) >= 3),
        "worst_block_at_least_minus_0_010": bool(min(paired_gain) >= -0.010),
        "mean_hug_share_increase_at_most_0_10": bool(float(np.mean(paired_hug_delta)) <= 0.10),
        "all_40_registered_cells_valid": True,
    }
    gate["passed"] = all(gate.values())

    base = np.asarray(fold_dti["T_BASE"], dtype=float)
    mag = np.asarray(fold_dti["T_PLUS_PSG"], dtype=float)
    grav = np.asarray(fold_dti["T_PLUS_GRAV"], dtype=float)
    both = np.asarray(fold_dti["T_PLUS_PSG_GRAV"], dtype=float)
    psg_effect = 0.5 * ((mag - base) + (both - grav))
    grav_effect = 0.5 * ((grav - base) + (both - mag))
    interaction = both - mag - grav + base
    arm_means = {
        arm: float(np.mean([lookup[(fold, draw, arm)]["dti"] for fold in range(4) for draw in draws]))
        for arm in ARMS
    }
    hug_means = {
        arm: float(np.mean([lookup[(fold, draw, arm)]["hug"] for fold in range(4) for draw in draws]))
        for arm in ARMS
    }
    per_cell = [
        {
            "fold": row["fold_name"],
            "draw": row["draw"],
            "arm": row["arm"],
            "dti": row["dti"],
            "hug": row["hug"],
            "emitted": row["emitted"],
            "n_truth": row["n_truth"],
        }
        for row in rows
    ]

    screen_pass = gate["passed"] if stage == "screen" else None
    confirm_pass = gate["passed"] if stage == "confirm" else None
    result = {
        "schema_version": 1,
        "hypothesis": "H31 multiscale potential-field edge persistence (worming-like proxy)",
        "stage": stage,
        "preregistration": design["preregistration"],
        "preregistration_sha256": design["preregistration_sha256"],
        "design_sha256": internal["hashes"]["design_sha256"],
        "cells_sha256": internal["hashes"]["cells_sha256"],
        "design_bytes": internal["hashes"]["design_bytes"],
        "cells_bytes": internal["hashes"]["cells_bytes"],
        "row_count": len(rows),
        "draws": draws,
        "spatial_folds": FOLDS,
        "primary_candidate": CANDIDATE,
        "primary_candidate_mean_dti": arm_means[CANDIDATE],
        "same_run_arm_mean_dti": arm_means,
        "same_run_arm_mean_hug_share": hug_means,
        "fold_mean_dti": fold_dti,
        "fold_mean_hug_share": fold_hug,
        "best_control_arm_by_fold": chosen_control,
        "paired_gain_vs_best_same_run_control_by_fold": [float(v) for v in paired_gain],
        "paired_hug_share_change_by_fold": [float(v) for v in paired_hug_delta],
        "mean_paired_gain_vs_best_same_run_control": mean_gain,
        "positive_spatial_blocks": int(sum(v > 0 for v in paired_gain)),
        "worst_spatial_block_gain": float(min(paired_gain)),
        "mean_hug_share_change": float(np.mean(paired_hug_delta)),
        "gate": gate,
        "stage_gate_passed": bool(gate["passed"]),
        "screen_gate_passed": screen_pass,
        "confirmation_gate_passed": confirm_pass,
        "slot_eligible": False,
        "factorial_effects": {
            "pseudogravity_main_effect": _effect_summary(psg_effect.tolist()),
            "isostatic_gravity_main_effect": _effect_summary(grav_effect.tolist()),
            "pseudogravity_x_gravity_difference_in_differences": _effect_summary(interaction.tolist()),
        },
        "paired_cells": per_cell,
        "decision": (
            "Screen passed; fresh confirmation on draws 12,13 is permitted, but no candidate file or weekly slot is approved."
            if stage == "screen" and gate["passed"]
            else "Screen failed; stop and do not run confirmation or create a candidate TIFF."
            if stage == "screen"
            else "Fresh confirmation passed; this authorizes only a separate full-data build/review and exact-file audit, not a weekly submission."
            if gate["passed"]
            else "Fresh confirmation failed; stop and do not create a candidate TIFF or use a weekly submission slot."
        ),
        "limitations": [
            "These are catalogue-component hide-and-recover proxy scores, not official competition scores or hidden-fault truth.",
            "Owner-mirror inputs are hash-pinned but not organizer-authenticated.",
            "Four spatial quadrants are the replication units; draws are repeated hide realizations.",
            "H31 is a thresholded scale-space proxy, not a full Poisson-wavelet inversion or fault-depth estimate.",
        ],
    }
    return result


def write_result(run_dir: Path, result: dict) -> None:
    out_json = run_dir / "results.json"
    if out_json.exists():
        raise FileExistsError(f"refusing to overwrite existing analyzer output: {out_json}")
    out_json.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    rows = [
        f"# H31 {result['stage']} — multiscale potential-field edge persistence",
        "",
        f"**Primary candidate:** `{CANDIDATE}`. **Stage gate:** {'PASS' if result['stage_gate_passed'] else 'FAIL'}. **Slot eligible:** no.",
        "",
        f"Draws: {', '.join(map(str, result['draws']))}; four spatial blocks; {result['row_count']} validated model cells.",
        f"Mean paired gain versus best same-run control: {result['mean_paired_gain_vs_best_same_run_control']:+.6f}; positive blocks {result['positive_spatial_blocks']}/4; worst {result['worst_spatial_block_gain']:+.6f}; mean catalogue-hug change {result['mean_hug_share_change']:+.6f}.",
        "",
        "## Arm means",
        "",
        "| Arm | Mean DTI | Mean visible-catalogue hug share |",
        "|---|---:|---:|",
    ]
    for arm in ARMS:
        rows.append(f"| `{arm}` | {result['same_run_arm_mean_dti'][arm]:.6f} | {result['same_run_arm_mean_hug_share'][arm]:.6f} |")
    rows += [
        "",
        "## Registered factorial contrasts (four spatial blocks)",
        "",
        "| Contrast | Mean | Descriptive 95% t interval |",
        "|---|---:|---:|",
    ]
    for name, effect in result["factorial_effects"].items():
        interval = effect["descriptive_95pct_t_interval"]
        rows.append(f"| `{name}` | {effect['mean_across_four_spatial_blocks']:+.6f} | [{interval[0]:+.6f}, {interval[1]:+.6f}] |")
    rows += [
        "",
        "> These t intervals are descriptive only: there are four spatial blocks, not eight independent fold×draw cells.",
        "",
        "## Gate details",
        "",
    ]
    for key, passed in result["gate"].items():
        rows.append(f"- {'PASS' if passed else 'FAIL'} — `{key}`")
    rows += [
        "",
        result["decision"],
        "",
        "All values above are spatially blocked catalogue-gap **proxy** results; they are not competition scores. See `design.json` and `cells.jsonl` for the frozen design and raw outcomes.",
        "",
    ]
    md = run_dir / "results.md"
    if md.exists():
        raise FileExistsError(f"refusing to overwrite existing analyzer output: {md}")
    md.write_text("\n".join(rows))


def verify_passing_screen(screen_dir: Path) -> dict:
    """Recompute screen gate from raw hashes/results and block confirmation unless it genuinely passed."""
    result_path = screen_dir / "results.json"
    if not result_path.is_file():
        raise SystemExit("H31 screen results.json is missing; analyze the complete screen first")
    try:
        stored = json.loads(result_path.read_text())
        recomputed = analyze_run(screen_dir, "screen")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot validate H31 screen before confirmation: {exc}") from exc
    for key in (
        "design_sha256",
        "cells_sha256",
        "row_count",
        "draws",
        "stage_gate_passed",
        "screen_gate_passed",
        "confirmation_gate_passed",
        "gate",
        "mean_paired_gain_vs_best_same_run_control",
        "paired_gain_vs_best_same_run_control_by_fold",
        "positive_spatial_blocks",
        "worst_spatial_block_gain",
        "mean_hug_share_change",
        "same_run_arm_mean_dti",
        "factorial_effects",
    ):
        if stored.get(key) != recomputed.get(key):
            raise SystemExit(f"H31 screen stored result differs from recomputed raw evidence: {key}")
    if stored.get("stage_gate_passed") is not True:
        raise SystemExit("H31 preregistered screen gate failed; confirmation is not allowed")
    return recomputed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=None, help="run directory; default is the screen directory")
    parser.add_argument("--stage", choices=tuple(EXPECTED_DRAWS), default="screen")
    args = parser.parse_args()
    run_dir = Path(args.dir) if args.dir else ROOT / "evidence" / f"h31_worm_{args.stage}"
    result = analyze_run(run_dir, args.stage)
    write_result(run_dir, result)
    print(f"{args.stage} gate={'PASS' if result['stage_gate_passed'] else 'FAIL'}")
    print(f"Mean gain versus best same-run control: {result['mean_paired_gain_vs_best_same_run_control']:+.6f}")
    print(f"Positive spatial blocks: {result['positive_spatial_blocks']}/4; slot_eligible=False")
    print(f"Wrote {run_dir / 'results.json'} and {run_dir / 'results.md'}")


if __name__ == "__main__":
    main()
