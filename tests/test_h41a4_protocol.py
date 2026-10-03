"""Guards for the frozen H41-A4/H34-protocol stage (knowledge/27, session 5).

These tests pin the frozen protocol text against the runner's constants and, when the evidence is present in
the checkout, recompute the gates independently of the runner and of ``scripts/analyze_h41a4_h34protocol.py``.
"""

from __future__ import annotations

import json

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "knowledge" / "27_preregistered_h41a4_h34protocol_2026-10-03.md"
RUNNER = ROOT / "scripts" / "run_h41a4_h34protocol.py"
EVIDENCE = ROOT / "evidence" / "h41a4_h34protocol"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
HOLDOUT_BEST = 0.14479018210246675


def test_preregistration_and_runner_constants_agree() -> None:
    text = PREREG.read_text()
    assert "FROZEN before any fit" in text
    assert "**20, 21**" in text, "the frozen protocol must name the spent draws it reuses"
    assert "0.14479018210246675" in text, "the bar must be the recorded H34 best"
    assert "+0.005" in text and "−0.010" in text
    assert "3 of 4 folds" in text
    runner = RUNNER.read_text()
    assert "DRAWS = (20, 21)" in runner
    assert "HOLDOUT_BEST = 0.14479018210246675" in runner
    assert "mean_gain=0.005" in runner and "min_positive_folds=3" in runner
    assert "max_fold_loss=-0.010" in runner and "budget_ratio_band=(0.75, 1.25)" in runner
    assert "sgmc_min_positive_folds=3" in runner
    assert "refusing to run from a dirty worktree" in runner
    assert "refusing to overwrite existing evidence" in runner


def test_h41a4_evidence_recomputes_and_matches_the_stored_controls() -> None:
    cells_path = EVIDENCE / "cells.jsonl"
    if not cells_path.is_file() or not H34_CELLS.is_file():
        pytest.skip("H41-A4 stage evidence not present in this checkout")
    rows = [json.loads(line) for line in cells_path.read_text().splitlines() if line.strip()]
    summary = json.loads((EVIDENCE / "summary.json").read_text())
    design = json.loads((EVIDENCE / "design.json").read_text())
    assert len(rows) == 24, "4 folds x 2 draws x 3 arms"
    assert {r["arm"] for r in rows} == set(design["arms"]) == {"C0_base", "C1_geodesic_dots", "A4_h41_union"}
    assert sorted({r["draw"] for r in rows}) == [20, 21]
    assert design["gates"]["holdout_best"] == HOLDOUT_BEST

    def mean(arm: str, fold: int) -> float:
        vals = [r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold]
        return sum(vals) / len(vals)

    gains = [mean("A4_h41_union", fold) - max(mean("C0_base", fold), mean("C1_geodesic_dots", fold))
             for fold in range(4)]
    assert abs(sum(gains) / 4 - summary["gates"]["mean_gain"]) < 1e-12

    stored = {}
    for line in H34_CELLS.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if row["arm"] in ("C0_ordered_dots", "C1_geodesic_dots"):
                stored[(row["fold_name"], int(row["draw"]), row["arm"])] = float(row["dti"])
    deltas = []
    for row in rows:
        if row["arm"] == "C0_base":
            deltas.append(abs(row["dti"] - stored[(row["fold_name"], row["draw"], "C0_ordered_dots")]))
        elif row["arm"] == "C1_geodesic_dots":
            deltas.append(abs(row["dti"] - stored[(row["fold_name"], row["draw"], "C1_geodesic_dots")]))
    assert deltas, "the reproduction check needs the stored H34 control cells"
    assert max(deltas) <= design["gates"]["reproduction_tolerance"], (
        f"the frozen controls must reproduce the stored H34 cells; max |delta| = {max(deltas)}")

    analyzer = json.loads((EVIDENCE / "analyzer_report.json").read_text())
    assert analyzer["problems"] == []
    assert analyzer["recomputed"]["gate_checks"] == summary["gate_checks"]
    verdict = summary["verdict"]
    assert verdict.startswith(("SLOT-ELIGIBLE", "PRIMARY PASS", "NO PROMOTION", "NOT COMPARABLE")), verdict
    if not summary["gate_checks"]["G4"]:
        assert verdict.startswith("NOT COMPARABLE"), "a failed G4 must void the verdict, not soften it"
    if summary["gate_checks"]["G1"] and summary["gate_checks"]["G2"] and not summary["gate_checks"]["G3"]:
        assert verdict.startswith("PRIMARY PASS"), "primary gain with a negative secondary proxy is no promotion"
