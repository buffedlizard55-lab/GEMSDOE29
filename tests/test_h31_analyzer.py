from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from analyze_h31_worming import (
    CACHE_RECORD_NAMES,
    CANONICAL_MATRIX,
    DESIGN_SEED,
    EXPECTED_DRAWS,
    FOLDS,
    analyze_run,
    verify_passing_screen,
    write_result,
)
from gemsdoe.experiment import HGB_PARAMS, N_NEG
from gemsdoe.h30 import H30_BASE_EXTRAS
from gemsdoe.metric import ALPHA, BETA, EPS
from gemsdoe.submission import sha256_file
from gemsdoe.worms import H31_NAMES

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "knowledge" / "02_preregistered_h31_worming_2026-10-03.md"


def _screen_dir(tmp_path: Path, *, candidate_better: bool = True) -> Path:
    run_dir = tmp_path / "screen"
    run_dir.mkdir(parents=True)
    order = np.random.default_rng(DESIGN_SEED).permutation(len(CANONICAL_MATRIX)).tolist()
    randomized = [CANONICAL_MATRIX[index] for index in order]
    model_parameters = {
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
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    design = {
        "schema_version": 1,
        "stage": "screen",
        "draws": EXPECTED_DRAWS["screen"],
        "spatial_folds": FOLDS,
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "primary_candidate": "T_PLUS_PSG_GRAV",
        "feature_names": H31_NAMES,
        "feature_families": "BDE",
        "fixed_addons": H30_BASE_EXTRAS,
        "branch": "arena/01a10075-gemsdoe29",
        "clean_worktree_before_fit": True,
        "code_revision": "1" * 40,
        "execution_revision": "1" * 40,
        "design_seed": DESIGN_SEED,
        "canonical_matrix": CANONICAL_MATRIX,
        "row_order_zero_based": order,
        "randomized_matrix": randomized,
        "factorial_arms": ["T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV", "T_PLUS_PSG_GRAV"],
        "registered_controls": ["BASE_NO_TIP", "T_BASE", "T_PLUS_PSG", "T_PLUS_GRAV"],
        "fixed_tip_control": "H27_tip",
        "model": {"class": "sklearn.ensemble.HistGradientBoostingClassifier", "parameters": model_parameters},
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
            "k_fraction_of_scored_domain": 0.0245,
            "min_distance_px": 2.4,
        },
        "promotion_gate": {
            "mean_paired_gain_over_best_same_run_control": "> +0.001",
            "positive_spatial_blocks": ">= 3 of 4",
            "worst_spatial_block_gain": ">= -0.010",
            "catalogue_hug_share_increase": "<= +0.10",
            "fresh_confirmation_required": True,
        },
        "data_manifest_sha256_and_bytes": {
            item["id"]: {"sha256": item["sha256"], "bytes": item["bytes"]} for item in manifest["files"]
        },
        "work_cache_sha256_and_bytes": {
            name: {"sha256": (f"{index + 1:064x}"), "bytes": index + 1}
            for index, name in enumerate(CACHE_RECORD_NAMES)
        },
    }
    (run_dir / "design.json").write_text(json.dumps(design, indent=2) + "\n")

    factor_by_arm = {item["arm"]: (item["PSG"], item["GRAV"]) for item in CANONICAL_MATRIX}
    rows = []
    for fold in range(4):
        for draw in EXPECTED_DRAWS["screen"]:
            for run_order, arm in enumerate([row["arm"] for row in randomized], start=1):
                tp = 125.0 if (arm == "T_PLUS_PSG_GRAV" and candidate_better) else 100.0
                fp = 10.0
                n_truth = 200
                dti = tp / (tp + ALPHA * fp + BETA * (n_truth - tp) + EPS)
                rows.append(
                    {
                        "stage": "screen",
                        "fold": fold,
                        "fold_name": FOLDS[fold],
                        "draw": draw,
                        "run_order": run_order,
                        "arm": arm,
                        "PSG": factor_by_arm[arm][0],
                        "GRAV": factor_by_arm[arm][1],
                        "design_seed": DESIGN_SEED,
                        "k_fraction": 0.0245,
                        "min_distance_px": 2.4,
                        "auc": 0.7,
                        "dti": dti,
                        "coverage": tp / n_truth,
                        "tp": tp,
                        "fp": fp,
                        "n_truth": n_truth,
                        "emitted": 180,
                        "hug": 0.12,
                        "fit_s": 1.0,
                        "predict_s": 0.1,
                    }
                )
    (run_dir / "cells.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    return run_dir


def test_analyzer_recomputes_complete_screen_and_confirmation_gate(tmp_path: Path) -> None:
    run_dir = _screen_dir(tmp_path)
    result = analyze_run(run_dir, "screen")
    assert result["row_count"] == 40
    assert result["stage_gate_passed"] is True
    assert result["slot_eligible"] is False
    write_result(run_dir, result)
    checked = verify_passing_screen(run_dir)
    assert checked["stage_gate_passed"] is True


def test_analyzer_rejects_inconsistent_metrics_and_noninteger_draw(tmp_path: Path) -> None:
    run_dir = _screen_dir(tmp_path)
    path = run_dir / "cells.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["dti"] = 0.99
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="DTI is inconsistent"):
        analyze_run(run_dir, "screen")

    run_dir = _screen_dir(tmp_path / "float-draw")
    rows = [json.loads(line) for line in (run_dir / "cells.jsonl").read_text().splitlines()]
    rows[0]["draw"] = float(rows[0]["draw"])
    (run_dir / "cells.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="registered integer"):
        analyze_run(run_dir, "screen")


def test_confirmation_gate_refuses_failed_or_tampered_screen(tmp_path: Path) -> None:
    run_dir = _screen_dir(tmp_path, candidate_better=False)
    result = analyze_run(run_dir, "screen")
    assert result["stage_gate_passed"] is False
    write_result(run_dir, result)
    with pytest.raises(SystemExit, match="screen gate failed"):
        verify_passing_screen(run_dir)
