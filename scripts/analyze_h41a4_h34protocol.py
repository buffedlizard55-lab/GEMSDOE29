#!/usr/bin/env python3
"""Independently recompute the H41-A4/H34-protocol gates from the raw cells.

Reads only ``evidence/h41a4_h34protocol/cells.jsonl``, the frozen design record and the stored H34 control
cells, recomputes every gate with fresh code, and writes ``analyzer_report.json`` beside the evidence. Any
disagreement with ``summary.json`` is recorded as a problem instead of being smoothed over.

    python3 scripts/analyze_h41a4_h34protocol.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "h41a4_h34protocol"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
STAGE = "h41a4_h34protocol"


def load_cells(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    cells_path, summary_path = EVIDENCE / "cells.jsonl", EVIDENCE / "summary.json"
    if not cells_path.is_file() or not summary_path.is_file():
        raise SystemExit(f"missing {cells_path} or {summary_path}")
    rows = load_cells(cells_path)
    summary = json.loads(summary_path.read_text())
    design = json.loads((EVIDENCE / "design.json").read_text())
    gates = design["gates"]
    problems: list[str] = []

    folds = list(range(4))
    draws = list(design["draws"])
    arms = list(design["arms"])
    if len(rows) != len(folds) * len(draws) * len(arms):
        problems.append(f"expected {len(folds) * len(draws) * len(arms)} cells, found {len(rows)}")
    if {r["arm"] for r in rows} != set(arms):
        problems.append("arm set differs from the design record")
    if sorted({r["draw"] for r in rows}) != sorted(draws):
        problems.append("draw set differs from the design record")
    if not all(np.isfinite(r["dti"]) for r in rows):
        problems.append("non-finite DTI in raw cells")

    def mean(arm: str, fold: int) -> float:
        vals = [r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold]
        return float(np.mean(vals)) if vals else float("nan")

    def sgmc_mean(arm: str, fold: int) -> float:
        vals = [r["sgmc_dti"] for r in rows if r["arm"] == arm and r["fold"] == fold]
        return float(np.mean(vals)) if vals else float("nan")

    control = {fold: max(mean("C0_base", fold), mean("C1_geodesic_dots", fold)) for fold in folds}
    gains = [mean("A4_h41_union", fold) - control[fold] for fold in folds]
    sgmc_gains = [sgmc_mean("A4_h41_union", fold) - max(sgmc_mean("C0_base", fold), sgmc_mean("C1_geodesic_dots", fold))
                  for fold in folds]
    budget_ratios = []
    for fold in folds:
        for draw in draws:
            arm_rows = [r for r in rows if r["arm"] == "A4_h41_union" and r["fold"] == fold and r["draw"] == draw]
            c0_rows = [r for r in rows if r["arm"] == "C0_base" and r["fold"] == fold and r["draw"] == draw]
            if arm_rows and c0_rows:
                budget_ratios.append(arm_rows[0]["emitted"] / max(c0_rows[0]["emitted"], 1))

    stored = {}
    if H34_CELLS.is_file():
        for row in load_cells(H34_CELLS):
            if row["arm"] in ("C0_ordered_dots", "C1_geodesic_dots"):
                stored[(row["fold_name"], int(row["draw"]), row["arm"])] = float(row["dti"])
    reproduction = []
    for row in rows:
        key = (row["fold_name"], int(row["draw"]),
               "C0_ordered_dots" if row["arm"] == "C0_base" else "C1_geodesic_dots")
        if row["arm"] in ("C0_base", "C1_geodesic_dots") and key in stored:
            reproduction.append(abs(float(row["dti"]) - stored[key]))
    repro_max = float(max(reproduction)) if reproduction else float("nan")

    recomputed = dict(
        mean_gain=float(np.mean(gains)), fold_gains=[float(g) for g in gains], worst_fold=float(np.min(gains)),
        positive_folds=int(sum(g > 0 for g in gains)), cells_present=len(rows) == len(folds) * len(draws) * len(arms),
        a4_mean_dti=float(np.mean([r["dti"] for r in rows if r["arm"] == "A4_h41_union"])),
        control_means={str(k): float(v) for k, v in control.items()},
        sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
        sgmc_fold_gains=[float(g) for g in sgmc_gains],
        budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
        budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        budget_ok=bool(budget_ratios and min(budget_ratios) >= gates["budget_ratio_band"][0]
                       and max(budget_ratios) <= gates["budget_ratio_band"][1]),
        reproduction_max_abs_delta=repro_max, reproduction_cells=len(reproduction),
    )
    g1 = bool(recomputed["mean_gain"] >= gates["mean_gain"] and recomputed["positive_folds"] >= gates["min_positive_folds"]
              and recomputed["worst_fold"] >= gates["max_fold_loss"] and recomputed["budget_ok"])
    g2 = bool(recomputed["a4_mean_dti"] > gates["holdout_best"])
    g3 = bool(recomputed["sgmc_mean_gain"] >= gates["sgmc_min_mean_gain"]
              and recomputed["sgmc_positive_folds"] >= gates["sgmc_min_positive_folds"])
    g4 = bool(recomputed["cells_present"] and np.isfinite(repro_max) and repro_max <= gates["reproduction_tolerance"])
    recomputed["gate_checks"] = dict(G1=g1, G2=g2, G3=g3, G4=g4)

    reported = summary.get("gates", {})
    for key in ("mean_gain", "worst_fold", "sgmc_mean_gain"):
        if key in reported and abs(float(reported[key]) - recomputed[key]) > 1e-12:
            problems.append(f"summary {key} {reported[key]} != recomputed {recomputed[key]}")
    for key in ("positive_folds", "sgmc_positive_folds"):
        if key in reported and int(reported[key]) != recomputed[key]:
            problems.append(f"summary {key} {reported[key]} != recomputed {recomputed[key]}")
    if summary.get("gate_checks") != recomputed["gate_checks"]:
        problems.append(f"summary gate_checks {summary.get('gate_checks')} != recomputed {recomputed['gate_checks']}")

    report = dict(
        stage=STAGE, analyzer="scripts/analyze_h41a4_h34protocol.py", n_cells=len(rows),
        gates=gates, recomputed=recomputed, reported_gate_checks=summary.get("gate_checks"),
        reported_verdict=summary.get("verdict"), problems=problems,
        note=("Independently recomputed from raw cells; the stored H34 control cells define gate G4's "
              "reproduction test. Both DTIs are local proxies, not the organizer metric."),
    )
    (EVIDENCE / "analyzer_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: recomputed[k] for k in ("mean_gain", "worst_fold", "positive_folds", "a4_mean_dti",
                                                 "sgmc_mean_gain", "sgmc_positive_folds", "reproduction_max_abs_delta",
                                                 "gate_checks")}, indent=2))
    print("problems:", problems if problems else "none")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
