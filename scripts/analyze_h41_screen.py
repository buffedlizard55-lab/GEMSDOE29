#!/usr/bin/env python3
"""Independent verification of the H41 screen: recompute every gate from raw cells, never from the summary.

Follows the H31/H35 analyzer pattern: this script re-reads ``cells_<stage>.jsonl``, re-derives means, fold
gains, per-draw fold counts, budget ratios and gate booleans, cross-checks the frozen gate constants against
``design_screen.json`` and the preregistration hash, and reports any disagreement with the runner's own
``summary_<stage>.json`` as an integrity failure. It also checks the arm wiring (each arm must carry exactly
the number of H41 columns the frozen plan promises) so a mis-indexed column cannot hide inside a null result.

    python3 scripts/analyze_h41_screen.py [--dir evidence/h41_screen]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDS = (0, 1, 2, 3)
ARMS = ("C0_base", "A1_h41_off", "A2_h41_support", "A3_h41_corridor", "A4_h41_union")
ARM_EXTRA = {"C0_base": 0, "A1_h41_off": 2, "A2_h41_support": 4, "A3_h41_corridor": 4, "A4_h41_union": 5}
MEAN_GAIN = 0.005
MIN_POS_FOLDS = 3
WORST_FLOOR = -0.010
BAND = (0.75, 1.25)
HOLDOUT_BEST = 0.14479018210246675
MIN_NONZERO_FRACTION = 0.002
PREREG = ROOT / "knowledge" / "24_preregistered_h41_screen_2026-10-03.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def analyse_stage(rows: list[dict], draws: tuple[int, ...]) -> dict:
    out: dict[str, dict] = {}
    n_expect = len(FOLDS) * len(draws)
    for arm in ARMS:
        sel = [r for r in rows if r["arm"] == arm and r["draw"] in draws]
        control = {f: np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] in draws])
                   for f in FOLDS}
        entry: dict[str, object] = {"cells_present": len(sel)}
        entry["nonfinite_cells"] = len([r for r in sel
                                        if not all(math.isfinite(x) for x in (r["dti"], r["sgmc_dti"], r["emitted"]))])
        fold_means = {f: np.mean([r["dti"] for r in sel if r["fold"] == f]) for f in FOLDS}
        sgmc_means = {f: np.mean([r["sgmc_dti"] for r in sel if r["fold"] == f]) for f in FOLDS}
        fold_gain = {f: float(fold_means[f] - control[f]) for f in FOLDS}
        def pick(rows_, **kw):
            return next((r for r in rows_ if all(r[k] == v for k, v in kw.items())), None)

        pairs_missing = 0
        per_draw_pos = {}
        for d in draws:
            n_pos = 0
            for f in FOLDS:
                a, c = pick(sel, fold=f, draw=d), pick(rows, arm="C0_base", fold=f, draw=d)
                if a is None or c is None:
                    pairs_missing += 1
                    continue
                if a["dti"] - c["dti"] > 0:
                    n_pos += 1
            per_draw_pos[d] = n_pos
        budget_ratios = []
        for d in draws:
            for f in FOLDS:
                a, c = pick(sel, fold=f, draw=d), pick(rows, arm="C0_base", fold=f, draw=d)
                if a is None or c is None:
                    continue
                budget_ratios.append(a["emitted"] / max(c["emitted"], 1))
        entry["paired_cells_missing"] = pairs_missing
        entry.update(
            mean_dti=float(np.mean([r["dti"] for r in sel])) if sel else float("nan"),
            fold_gains=fold_gain,
            mean_gain=float(np.mean(list(fold_gain.values()))) if arm != "C0_base" else 0.0,
            positive_folds_per_draw=per_draw_pos,
            worst_fold_gain=min(fold_gain.values()) if arm != "C0_base" else 0.0,
            sgmc_fold_gains={f: float(sgmc_means[f] - np.mean([r["sgmc_dti"] for r in rows if r["arm"] == "C0_base"
                                                               and r["fold"] == f and r["draw"] in draws])) for f in FOLDS},
            budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
            budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        )
        if arm != "C0_base":
            entry["G1_PASS"] = bool(
                entry["mean_gain"] >= MEAN_GAIN
                and min(per_draw_pos.values()) >= MIN_POS_FOLDS
                and entry["worst_fold_gain"] >= WORST_FLOOR
                and entry["cells_present"] == n_expect and not pairs_missing
                and not entry["nonfinite_cells"]
                and (entry["budget_ratio_min"] if entry["budget_ratio_min"] is not None else -1) >= BAND[0]
                and (entry["budget_ratio_max"] if entry["budget_ratio_max"] is not None else 9e9) <= BAND[1]
            )
            entry["sgmc_positive_folds"] = int(sum(v > 0 for v in entry["sgmc_fold_gains"].values()))
            entry["above_holdout_best"] = bool(entry["mean_dti"] > HOLDOUT_BEST)
        out[arm] = entry
    return out


def wiring_problems(rows: list[dict]) -> list[str]:
    """Every arm must carry the frozen column count, and the H41 diagnostics must be present on the control."""
    problems: list[str] = []
    base = [r["n_features"] for r in rows if r["arm"] == "C0_base"]
    if not base:
        return ["no C0_base cells"]
    for arm, extra in ARM_EXTRA.items():
        sel = [r for r in rows if r["arm"] == arm]
        if not sel:
            continue
        bad = [r for r in sel if r["n_features"] != base[0] + extra]
        if bad:
            problems.append(f"{arm}: {len(bad)} cells with n_features != base({base[0]})+{extra}")
    if any("h41_diag" not in r for r in rows if r["arm"] == "C0_base"):
        problems.append("a C0_base cell is missing h41_diag")
    guard = [p for r in rows if r["arm"] == "C0_base" for p in r.get("viability_guard", [])]
    if guard:
        problems.append(f"viability guard reported {len(guard)} sparse-column problems: {guard[:3]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(ROOT / "evidence" / "h41_screen"))
    args = ap.parse_args()
    base = Path(args.dir)
    report: dict[str, dict] = {}
    problems: list[str] = []
    for stage, draws in (("screen", (28, 29)), ("confirm", (30, 31))):
        cells = base / f"cells_{stage}.jsonl"
        if not cells.is_file():
            continue
        rows = load_rows(cells)
        problems.extend(f"{stage}: {p}" for p in wiring_problems(rows))
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
            vguard = summary.get("viability_guard", {})
            if vguard.get("min_nonzero_fraction") != MIN_NONZERO_FRACTION:
                problems.append(f"{stage}: summary guard floor {vguard.get('min_nonzero_fraction')} != frozen {MIN_NONZERO_FRACTION}")
            # consistent means: passed is true exactly when the problem list is empty. (An earlier version of
            # this line compared the two booleans with != and so flagged every clean run; found and corrected
            # on 2026-10-03 after the screen finished. It checks a bookkeeping flag only - no gate, threshold
            # or cell value is involved, and the correction is disclosed as IR-29-H41-ANALYZER-GUARD-BUG.)
            if bool(vguard.get("problems", [])) == bool(vguard.get("passed", True)):
                problems.append(f"{stage}: viability_guard passed={vguard.get('passed')} is inconsistent with "
                                f"{len(vguard.get('problems', []))} recorded problem(s)")
        report[stage] = {"draws": list(draws), "n_cells": len(rows), "arms": mine, "summary_cross_check": cross}
    design = base / "design_screen.json"
    design_check: dict[str, object] = {}
    if design.is_file():
        d = json.loads(design.read_text())
        g = d["gates"]
        ok = (g["mean_gain"] == MEAN_GAIN and g["min_positive_folds"] == MIN_POS_FOLDS
              and g["max_fold_loss"] == WORST_FLOOR and tuple(g["budget_ratio_band"]) == BAND
              and abs(g["holdout_best"] - HOLDOUT_BEST) < 1e-12
              and g["min_nonzero_fraction"] == MIN_NONZERO_FRACTION)
        design_check["gates_match"] = ok
        if not ok:
            problems.append("analyzer gate constants disagree with design_screen.json")
        design_check["draws"] = d["draws"]
        design_check["arms"] = d["arms"]
        design_check["arm_columns_frozen"] = all(
            len(d["arm_columns"][a]) == ARM_EXTRA[a] for a in ARMS)
        if not design_check["arm_columns_frozen"]:
            problems.append("design arm column plan disagrees with the analyzer's frozen ARM_EXTRA counts")
        if d.get("preregistration", {}).get("path"):
            pread = ROOT / d["preregistration"]["path"]
            same = pread.is_file() and sha256_file(pread) == d["preregistration"]["sha256"]
            design_check["prereg_hash_matches_current_file"] = same
            if not same:
                problems.append("the preregistration file changed after the run was designed (hash mismatch)")
    else:
        design_check["design_screen_missing"] = True
    if not PREREG.is_file():
        problems.append(f"missing frozen preregistration {PREREG.relative_to(ROOT)}")
    payload = dict(
        generated_by="scripts/analyze_h41_screen.py",
        date="2026-10-03",
        gates=dict(mean_gain=MEAN_GAIN, min_positive_folds=MIN_POS_FOLDS, worst_floor=WORST_FLOOR,
                   budget_band=list(BAND), holdout_best=HOLDOUT_BEST,
                   min_nonzero_fraction=MIN_NONZERO_FRACTION),
        design_check=design_check,
        note=("Independent recomputation from raw cells only; summary cross-checked. Gate constants copied "
              "from knowledge/24_preregistered_h41_screen_2026-10-03.md §4. DTI here is the catalogue-hidden "
              "spatial proxy, not a competition score."),
        integrity_problems=problems,
        report=report,
    )
    out_path = base / "analyzer_report.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({s: {a: {k: v for k, v in e.items()
                              if k in ("mean_gain", "G1_PASS", "mean_dti", "above_holdout_best", "cells_present",
                                       "positive_folds_per_draw", "worst_fold_gain")}
                        for a, e in r["arms"].items()} for s, r in report.items()}, indent=2))
    print("problems:", problems if problems else "none")
    print(f"wrote {out_path}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
