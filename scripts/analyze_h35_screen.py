#!/usr/bin/env python3
"""Independent verification of the H35/H40 screen: recompute every gate from raw cells, not from the
summary. Follows the H31 analyzer pattern (scripts/analyze_h31_worming.py): this script never trusts
``summary_*.json``; it re-reads ``cells_*.jsonl``, re-derives means, folds, draws, budgets, and gate
booleans, and reports any disagreement with the runner's own summary as an integrity failure.

    python3 scripts/analyze_h35_screen.py [--dir evidence/h35_h40_screen]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDS = (0, 1, 2, 3)
ARMS = ("C0_base", "A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union")
MEAN_GAIN = 0.005
MIN_POS_FOLDS = 3
WORST_FLOOR = -0.010
BAND = (0.75, 1.25)
HOLDOUT_BEST = 0.14479018210246675


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def analyse_stage(rows: list[dict], draws: tuple[int, ...]) -> dict:
    out: dict[str, dict] = {}
    n_expect = len(FOLDS) * len(draws)
    for arm in ARMS:
        sel = [r for r in rows if r["arm"] == arm and r["draw"] in draws]
        control = {f: np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] in draws]) for f in FOLDS}
        entry: dict[str, object] = {"cells_present": len(sel)}
        bad_cells = [r for r in sel if not all(math.isfinite(x) for x in (r["dti"], r["sgmc_dti"], r["emitted"]))]
        entry["nonfinite_cells"] = len(bad_cells)
        fold_means = {f: np.mean([r["dti"] for r in sel if r["fold"] == f]) for f in FOLDS}
        sgmc_means = {f: np.mean([r["sgmc_dti"] for r in sel if r["fold"] == f]) for f in FOLDS}
        fold_gain = {f: float(fold_means[f] - control[f]) for f in FOLDS}
        per_draw_pos = {}
        for d in draws:
            per_draw_pos[d] = sum(
                1 for f in FOLDS
                if (next(r["dti"] for r in sel if r["fold"] == f and r["draw"] == d)
                    - next(r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] == d)) > 0
            )
        budget_ratios = []
        for d in draws:
            for f in FOLDS:
                a = next(r for r in sel if r["fold"] == f and r["draw"] == d)
                c = next(r for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] == d)
                budget_ratios.append(a["emitted"] / max(c["emitted"], 1))
        entry.update(
            mean_dti=float(np.mean([r["dti"] for r in sel])) if sel else float("nan"),
            fold_gains=fold_gain,
            mean_gain=float(np.mean(list(fold_gain.values()))) if arm != "C0_base" else 0.0,
            positive_folds_per_draw=per_draw_pos,
            worst_fold_gain=min(fold_gain.values()) if arm != "C0_base" else 0.0,
            sgmc_fold_gains={f: float(sgmc_means[f] - np.mean([r["sgmc_dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] in draws])) for f in FOLDS},
            budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
            budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        )
        if arm != "C0_base":
            entry["G1_PASS"] = bool(
                entry["mean_gain"] >= MEAN_GAIN
                and min(per_draw_pos.values()) >= MIN_POS_FOLDS
                and entry["worst_fold_gain"] >= WORST_FLOOR
                and entry["cells_present"] == n_expect
                and not bad_cells
                and entry["budget_ratio_min"] >= BAND[0]
                and entry["budget_ratio_max"] <= BAND[1]
            )
            entry["sgmc_positive_folds"] = int(sum(v > 0 for v in entry["sgmc_fold_gains"].values()))
            entry["above_holdout_best"] = bool(entry["mean_dti"] > HOLDOUT_BEST)
        out[arm] = entry
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(ROOT / "evidence" / "h35_h40_screen"))
    args = ap.parse_args()
    base = Path(args.dir)
    report: dict[str, dict] = {}
    problems: list[str] = []
    for stage, draws in (("screen", (24, 25)), ("confirm", (26, 27))):
        cells = base / f"cells_{stage}.jsonl"
        if not cells.is_file():
            continue
        rows = load_rows(cells)
        mine = analyse_stage(rows, draws)
        summary_path = base / f"summary_{stage}.json"
        cross: dict[str, float] = {}
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text())
            keymap = {"mean_gain": "mean_gain", "mean_dti": "mean_dti", "G1_SCREEN_PASS": "G1_PASS"}
            for arm, entry in mine.items():
                theirs = summary["arms"].get(arm, {})
                for their_key, my_key in keymap.items():
                    if their_key not in theirs or my_key not in entry:
                        continue
                    t, m = theirs[their_key], entry[my_key]
                    agree = bool(t) == bool(m) if isinstance(m, bool) else abs(float(t) - float(m)) < 1e-12
                    cross[f"{arm}.{their_key}"] = float(agree)
                    if not agree:
                        problems.append(f"{stage}.{arm}.{their_key}: summary={t!r} recomputed={m!r}")
        report[stage] = {"draws": list(draws), "arms": mine, "summary_cross_check": cross}
    payload = dict(
        generated_by="scripts/analyze_h35_screen.py",
        date="2026-10-03",
        gates=dict(mean_gain=MEAN_GAIN, min_positive_folds=MIN_POS_FOLDS, worst_floor=WORST_FLOOR,
                   budget_band=list(BAND), holdout_best=HOLDOUT_BEST),
        note=("Independent recomputation from raw cells only; summary cross-checked. Gate constants copied "
              "from knowledge/19_preregistered_h35_h40_screen_2026-10-03.md §4 and re-verified against "
              "design_screen.json when present."),
        integrity_problems=problems,
        report=report,
    )
    design = base / "design_screen.json"
    if design.is_file():
        d = json.loads(design.read_text())
        g = d["gates"]
        ok = (g["mean_gain"] == MEAN_GAIN and g["min_positive_folds"] == MIN_POS_FOLDS
              and g["max_fold_loss"] == WORST_FLOOR and tuple(g["budget_ratio_band"]) == BAND
              and abs(g["holdout_best"] - HOLDOUT_BEST) < 1e-12)
        payload["design_gate_match"] = ok
        if not ok:
            problems.append("analyzer gate constants disagree with design_screen.json")
    out_path = base / "analyzer_report.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({s: {a: {k: v for k, v in e.items() if k in ("mean_gain", "G1_PASS", "mean_dti", "above_holdout_best", "cells_present")}
                          for a, e in r["arms"].items()} for s, r in report.items()}, indent=2))
    print("problems:", problems if problems else "none")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
