#!/usr/bin/env python3
"""Independent analyzer for the H53 screen: recompute every gate from the raw cells.

Reads ``evidence/h53_screen/cells.jsonl`` + ``design.json`` and the stored
``evidence/h34_coverage_screen/cells.jsonl``, recomputes the gate numbers from scratch (no import of the
runner's gate code) and writes ``analyzer_report.json`` with an explicit ``integrity_problems`` list.
Nothing here fits a model or reads a raster.

    python3 scripts/analyze_h53_screen.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import work_dir  # noqa: E402
EVIDENCE = ROOT / "evidence" / "h53_screen"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
PREREG = ROOT / "knowledge" / "41_preregistered_h53_screen_2026-10-03.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def per_fold_mean(rows: list[dict], arm: str, field: str, fold: str) -> float:
    values = [r[field] for r in rows if r["arm"] == arm and r["fold_name"] == fold]
    return float(np.mean(values)) if values else float("nan")


def summarize_screen(rows: list[dict], design: dict) -> dict:
    gates = design["gates"]
    arms = [a for a in design["arms"] if a.startswith("A")]
    folds = design["folds"]
    draws = design["screen_draws"]
    out: dict = {}
    for arm in arms:
        gains = []
        sgmc_gains = []
        positives_per_draw = []
        budgets = []
        for draw in draws:
            pos = 0
            for fold in folds:
                control = max(per_fold_mean([r for r in rows if r["draw"] == draw], "C0_base", "dti", fold),
                              per_fold_mean([r for r in rows if r["draw"] == draw], "C1_geodesic_dots", "dti", fold))
                gain = per_fold_mean([r for r in rows if r["draw"] == draw], arm, "dti", fold) - control
                gains.append(gain)
                pos += int(gain > 0)
                sgmc_control = max(
                    per_fold_mean([r for r in rows if r["draw"] == draw], "C0_base", "sgmc_dti", fold),
                    per_fold_mean([r for r in rows if r["draw"] == draw], "C1_geodesic_dots", "sgmc_dti", fold))
                sgmc_gains.append(per_fold_mean([r for r in rows if r["draw"] == draw], arm, "sgmc_dti", fold)
                                  - sgmc_control)
                arm_row = next((r for r in rows if r["arm"] == arm and r["draw"] == draw and r["fold_name"] == fold), None)
                c1_row = next((r for r in rows if r["arm"] == "C1_geodesic_dots" and r["draw"] == draw
                               and r["fold_name"] == fold), None)
                if arm_row and c1_row:
                    budgets.append(arm_row["emitted"] / max(c1_row["emitted"], 1))
            positives_per_draw.append(pos)
        lo, hi = gates["budget_ratio_band"]
        mean_gain = float(np.mean(gains))
        worst = float(np.min(gains))
        g1 = bool(mean_gain >= gates["mean_gain"]
                  and all(p >= gates["min_positive_folds"] for p in positives_per_draw)
                  and worst >= gates["max_fold_loss"]
                  and bool(budgets) and all(lo <= b <= hi for b in budgets))
        cells_present = sum(1 for r in rows if r["arm"] == arm)
        out[arm] = dict(mean_gain=mean_gain, fold_gains=gains, positive_folds_per_draw=positives_per_draw,
                        worst_fold_gain=worst, budget_ok=bool(budgets) and all(lo <= b <= hi for b in budgets),
                        budget_ratio_min=float(np.min(budgets)) if budgets else None,
                        budget_ratio_max=float(np.max(budgets)) if budgets else None,
                        sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_fold_gains=sgmc_gains,
                        sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
                        mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == arm])),
                        mean_auc=float(np.nanmean([r.get("auc", np.nan) for r in rows if r["arm"] == arm])),
                        cells_present=cells_present, G1_SCREEN_PASS=g1)
    return out


def main() -> int:
    report_path = EVIDENCE / "analyzer_report.json"
    if report_path.exists():
        raise SystemExit(f"refusing to overwrite {report_path}")
    design = json.loads((EVIDENCE / "design.json").read_text())
    rows = load_rows(EVIDENCE / "cells.jsonl")
    stored = {(r["fold_name"], int(r["draw"]), r["arm"]): float(r["dti"]) for r in load_rows(H34_CELLS)}
    problems: list[str] = []

    if sha256_file(PREREG) != design["preregistration"]["sha256"]:
        problems.append("frozen preregistration hash does not match design.json")
    for name, digest in design["modules"].items():
        if sha256_file(ROOT / name) != digest:
            problems.append(f"module changed since design frozen: {name}")
    for name, digest in design["h53_fields"]["cache_sha256"].items():
        path = work_dir() / name
        if not path.is_file():
            problems.append(f"field cache missing: {name}")
            continue
        if name.endswith(".npy"):
            # The field data itself must be byte-identical to the launch cache.
            if sha256_file(path) != digest:
                problems.append(f"field cache changed since design frozen: {name}")
            continue
        # The JSON sidecar carries volatile build metadata (generated_utc, elapsed_s), so it is compared
        # field-by-field on the substance: the config and the diagnostics that the design froze.
        sidecar = json.loads(path.read_text())
        frozen = design["h53_fields"]
        for key in ("config", "diagnostics"):
            if key in frozen and sidecar.get(key) != frozen.get(key):
                problems.append(f"field cache sidecar {name}: {key} differs from design.json")

    repro_rows = [r for r in rows if r["phase"] == "reproduction"]
    screen_rows = [r for r in rows if r["phase"] == "screen"]
    expected_repro = len(design["reproduction_arms"]) * len(design["folds"]) * len(design["reproduction_draws"])
    expected_screen = len(design["arms"]) * len(design["folds"]) * len(design["screen_draws"])
    if len(repro_rows) != expected_repro:
        problems.append(f"reproduction phase has {len(repro_rows)} rows, expected {expected_repro}")
    if len(screen_rows) != expected_screen:
        problems.append(f"screen phase has {len(screen_rows)} rows, expected {expected_screen}")

    reproduction = []
    for row in repro_rows:
        key = (row["fold_name"], int(row["draw"]),
               "C0_ordered_dots" if row["arm"] == "C0_base" else row["arm"])
        if key in stored:
            reproduction.append(dict(fold_name=row["fold_name"], draw=row["draw"], arm=row["arm"],
                                     rebuilt=float(row["dti"]), stored=float(stored[key]),
                                     delta=float(row["dti"]) - float(stored[key])))
    repro_max = float(max((abs(i["delta"]) for i in reproduction), default=float("nan")))
    if not reproduction:
        problems.append("no reproduction comparisons available")
    elif repro_max > design["gates"]["reproduction_tolerance"]:
        problems.append(f"control reproduction max |delta| {repro_max:.3e} exceeds tolerance")

    for row in rows:
        if not np.isfinite(row["dti"]) or not np.isfinite(row["sgmc_dti"]):
            problems.append(f"non-finite score in {row['phase']} {row['fold_name']} d{row['draw']} {row['arm']}")

    summary = summarize_screen(screen_rows, design)
    primary = design["primary_arm"]
    gate_checks = dict(summary[primary]) if primary in summary else {}

    nonzero = design["h53_fields"]["diagnostics"]["nonzero_fraction"]
    viability_problems = [f"{k}: nonzero fraction {v:.6f} < {design['gates']['min_nonzero_fraction']}"
                          for k, v in nonzero.items() if v < design["gates"]["min_nonzero_fraction"]]
    problems.extend(viability_problems)
    identical = int(sum(int(r["identical_to_c1"]) for r in screen_rows if r["arm"] == primary))
    split_cells = int(sum(1 for r in screen_rows if r["arm"] == primary
                          and (r.get("feature_diag") or {}).get("h53_splits", 0) > 0))

    G1 = bool(gate_checks.get("G1_SCREEN_PASS", False))
    G2 = bool(gate_checks.get("mean_dti", 0.0) > design["gates"]["holdout_best"])
    G3 = bool(gate_checks.get("sgmc_mean_gain", -1.0) >= design["gates"]["sgmc_min_mean_gain"]
              and gate_checks.get("sgmc_positive_folds", 0) >= design["gates"]["sgmc_min_positive_folds"])
    G4 = bool(len(repro_rows) == expected_repro and len(screen_rows) == expected_screen
              and np.isfinite(repro_max) and repro_max <= design["gates"]["reproduction_tolerance"]
              and not any("non-finite" in p for p in problems))
    G5 = bool(not viability_problems and identical < 8)
    G6 = bool(split_cells >= design["gates"]["min_split_cells_for_feature_arm"])

    if not G4:
        verdict = "NOT COMPARABLE: integrity/reproduction failed; no verdict is issued."
    elif not (G5 and G6):
        verdict = "FAIL-INERT: the columns are either too sparse or cannot change the emission; no promotion."
    elif G1 and G2 and G3:
        verdict = "SLOT-ELIGIBLE by the frozen rule: a cross-fitted candidate artifact may be built for owner review."
    elif G1 and G2 and not G3:
        verdict = "PRIMARY PASS, SECONDARY-PROXY CONFLICT: no promotion (the H41/H43 outcome)."
    else:
        verdict = "NO PROMOTION: the H53 arms do not clear the frozen gates on fresh draws 36/37."

    payload = dict(
        schema_version=1,
        screen=dict(n_cells=len(screen_rows), draws=design["screen_draws"], arms=design["arms"],
                    arms_summary={a: dict(mean_dti=summary[a]["mean_dti"], mean_auc=summary[a]["mean_auc"],
                                          mean_gain=summary[a]["mean_gain"],
                                          positive_folds_per_draw=summary[a]["positive_folds_per_draw"],
                                          worst_fold_gain=summary[a]["worst_fold_gain"],
                                          budget_ratio_min=summary[a]["budget_ratio_min"],
                                          budget_ratio_max=summary[a]["budget_ratio_max"])
                                  for a in summary}),
        controls={a: float(np.mean([r["dti"] for r in screen_rows if r["arm"] == a]))
                  for a in ("C0_base", "C1_geodesic_dots")},
        primary=dict(arm=primary, **{k: v for k, v in gate_checks.items()}),
        gates=dict(G1=G1, G2=G2, G3=G3, G4=G4, G5=G5, G6=G6,
                   bar=design["gates"]["holdout_best"],
                   identical_to_c1_cells=identical, split_cells=split_cells,
                   h53_nonzero_fraction=nonzero, viability_problems=viability_problems),
        reproduction=dict(cells=len(repro_rows), expected=expected_repro, max_abs_delta=repro_max,
                          comparisons=reproduction),
        design=dict(draws=design["screen_draws"], arms=design["arms"], primary_arm=primary,
                    preregistration_sha256=design["preregistration"]["sha256"],
                    h53_config=design["h53_fields"]["config"]),
        integrity_problems=problems,
        verdict=verdict,
    )
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: payload["gates"][k] for k in ("G1", "G2", "G3", "G4", "G5", "G6")}, sort_keys=True))
    for arm in ("A1_h53_persist", "A2_h53_off", "A3_h53_scarp"):
        if arm in summary:
            print(f"{arm:16s} mean_gain {summary[arm]['mean_gain']:+.6f} folds+ {summary[arm]['positive_folds_per_draw']} "
                  f"worst {summary[arm]['worst_fold_gain']:+.6f} dti {summary[arm]['mean_dti']:.5f} "
                  f"sgmc {summary[arm]['sgmc_mean_gain']:+.6f} ({summary[arm]['sgmc_positive_folds']}/4)")
    print("integrity_problems:", problems if problems else "[]")
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
