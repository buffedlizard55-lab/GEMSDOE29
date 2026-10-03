#!/usr/bin/env python3
"""Independent verification of the H43 screen: recompute every gate from raw cells, never from the summary.

Follows the H31/H35/H41 analyzer pattern: this script re-reads ``cells_<stage>.jsonl``, re-derives means, fold
gains, per-draw fold counts, budget ratios and gate booleans (including the SGMC secondary-proxy gate and G3
promotion eligibility), cross-checks the frozen gate constants against ``design_screen.json`` and the
preregistration hash, and reports any disagreement with the runner's own ``summary_<stage>.json`` as an
integrity failure.

    python3 scripts/analyze_h43_screen.py [--dir evidence/h43_screen]
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
ARMS = ("C0_base", "A1_h43_off_front", "A2_h43_omega_area", "A3_h43_scarp_free", "A4_h43_union")
ARM_EXTRA = {
    "C0_base": 0,
    "A1_h43_off_front": 2,
    "A2_h43_omega_area": 3,
    "A3_h43_scarp_free": 4,
    "A4_h43_union": 5,
}
MEAN_GAIN = 0.005
MIN_POS_FOLDS = 3
WORST_FLOOR = -0.010
BAND = (0.75, 1.25)
SGMC_MIN_POS_FOLDS = 3
HOLDOUT_BEST = 0.14479018210246675
MIN_NONZERO_FRACTION = 0.002
PREREG = ROOT / "knowledge" / "27b_preregistered_h43b_screen_2026-10-03.md"


def _sgmc_mean(entry: dict) -> float | None:
    gains = entry.get("sgmc_fold_gains")
    if isinstance(gains, dict) and gains:
        return round(float(np.mean(list(gains.values()))), 9)
    return entry.get("sgmc_mean_gain")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def analyse_stage(rows: list[dict], draws: tuple[int, ...]) -> dict:
    out: dict[str, dict] = {}
    n_expect = len(FOLDS) * len(draws)
    for arm in ARMS:
        sel = [r for r in rows if r["arm"] == arm and r["draw"] in draws]
        control = {
            f: np.mean([r["dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] in draws])
            for f in FOLDS
        }
        entry: dict[str, object] = {"cells_present": len(sel)}
        entry["nonfinite_cells"] = len(
            [r for r in sel if not all(math.isfinite(x) for x in (r["dti"], r["sgmc_dti"], r["emitted"]))]
        )
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
            mean_auc=float(np.mean([r["auc"] for r in sel])) if sel else float("nan"),
            fold_gains=fold_gain,
            mean_gain=float(np.mean(list(fold_gain.values()))) if arm != "C0_base" else 0.0,
            positive_folds_per_draw=per_draw_pos,
            worst_fold_gain=min(fold_gain.values()) if arm != "C0_base" else 0.0,
            sgmc_fold_gains={
                f: float(
                    sgmc_means[f]
                    - np.mean(
                        [r["sgmc_dti"] for r in rows if r["arm"] == "C0_base" and r["fold"] == f and r["draw"] in draws]
                    )
                )
                for f in FOLDS
            },
            budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
            budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        )
        if arm != "C0_base":
            entry["G1_PASS"] = bool(
                entry["mean_gain"] >= MEAN_GAIN
                and min(per_draw_pos.values()) >= MIN_POS_FOLDS
                and entry["worst_fold_gain"] >= WORST_FLOOR
                and entry["cells_present"] == n_expect
                and not pairs_missing
                and not entry["nonfinite_cells"]
                and (entry["budget_ratio_min"] if entry["budget_ratio_min"] is not None else -1) >= BAND[0]
                and (entry["budget_ratio_max"] if entry["budget_ratio_max"] is not None else 9e9) <= BAND[1]
            )
            sgmc_pos = int(sum(v > 0 for v in entry["sgmc_fold_gains"].values()))
            entry["sgmc_positive_folds"] = sgmc_pos
            entry["sgmc_gate_pass"] = bool(sgmc_pos >= SGMC_MIN_POS_FOLDS)
            entry["above_holdout_best"] = bool(entry["mean_dti"] > HOLDOUT_BEST)
        out[arm] = entry
    return out


def wiring_problems(rows: list[dict]) -> list[str]:
    """Every arm must carry the frozen column count, and the H43 diagnostics must be present on the control."""
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
    if any("h43_diag" not in r for r in rows if r["arm"] == "C0_base"):
        problems.append("a C0_base cell is missing h43_diag")
    guard = [p for r in rows if r["arm"] == "C0_base" for p in r.get("viability_guard", [])]
    if guard:
        problems.append(f"viability guard reported {len(guard)} sparse-column problems: {guard[:3]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(ROOT / "evidence" / "h43b_screen"))
    args = ap.parse_args()
    base = Path(args.dir)
    report: dict[str, dict] = {}
    problems: list[str] = []
    for stage, draws in (("screen", (32, 33)), ("confirm", (34, 35))):
        cells = base / f"cells_{stage}.jsonl"
        if not cells.is_file():
            continue
        rows = load_rows(cells)
        problems.extend(f"{stage}: {p}" for p in wiring_problems(rows))
        mine = analyse_stage(rows, draws)
        summary_path = base / f"summary_{stage}.json"
        cross: dict[str, float] = {}
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            keymap = {
                "mean_gain": "mean_gain",
                "mean_dti": "mean_dti",
                "G1_SCREEN_PASS": "G1_PASS",
                "sgmc_gate_pass": "sgmc_gate_pass",
            }
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
                problems.append(
                    f"{stage}: summary guard floor {vguard.get('min_nonzero_fraction')} != frozen {MIN_NONZERO_FRACTION}"
                )
            if bool(vguard.get("problems", [])) == bool(vguard.get("passed", True)):
                problems.append(
                    f"{stage}: viability_guard passed={vguard.get('passed')} is inconsistent with "
                    f"{len(vguard.get('problems', []))} recorded problem(s)"
                )
        report[stage] = {"draws": list(draws), "n_cells": len(rows), "arms": mine, "summary_cross_check": cross}
    design = base / "design_screen.json"
    design_check: dict[str, object] = {}
    if design.is_file():
        d = json.loads(design.read_text(encoding="utf-8"))
        g = d["gates"]
        ok = (
            g["mean_gain"] == MEAN_GAIN
            and g["min_positive_folds"] == MIN_POS_FOLDS
            and g["max_fold_loss"] == WORST_FLOOR
            and tuple(g["budget_ratio_band"]) == BAND
            and g["sgmc_min_positive_folds"] == SGMC_MIN_POS_FOLDS
            and abs(g["holdout_best"] - HOLDOUT_BEST) < 1e-12
            and g["min_nonzero_fraction"] == MIN_NONZERO_FRACTION
        )
        design_check["gates_match"] = ok
        if not ok:
            problems.append("analyzer gate constants disagree with design_screen.json")
        design_check["draws"] = d["draws"]
        design_check["arms"] = d["arms"]
        design_check["arm_columns_frozen"] = all(len(d["arm_columns"][a]) == ARM_EXTRA[a] for a in ARMS)
        if not design_check["arm_columns_frozen"]:
            problems.append("design arm column plan disagrees with the analyzer's frozen ARM_EXTRA counts")
        if d.get("preregistration", {}).get("sha256"):
            pread = PREREG if PREREG.is_file() else ROOT / d["preregistration"]["path"]
            same = pread.is_file() and sha256_file(pread) == d["preregistration"]["sha256"]
            design_check["prereg_hash_matches_current_file"] = same
            design_check["prereg_reconciled_path"] = str(pread.relative_to(ROOT))
            if not same:
                problems.append("the preregistration file changed after the run was designed (hash mismatch)")
    else:
        design_check["design_screen_missing"] = True
    if not PREREG.is_file():
        problems.append(f"missing frozen preregistration {PREREG.relative_to(ROOT)}")

    promotion = {}
    if "screen" in report:
        has_confirm = "confirm" in report
        for arm in ARMS:
            if arm == "C0_base":
                continue
            sc = report["screen"]["arms"].get(arm, {})
            cf = report["confirm"]["arms"].get(arm, {}) if has_confirm else {}
            checks = {
                "G1_screen_pass": bool(sc.get("G1_PASS")),
                "G2_confirmation_pass": bool(cf.get("G1_PASS")) if has_confirm else False,
                "screen_mean_above_holdout_best": bool(sc.get("mean_dti", -1) > HOLDOUT_BEST),
                "confirm_mean_above_holdout_best": bool(cf.get("mean_dti", -1) > HOLDOUT_BEST) if has_confirm else False,
                "sgmc_positive_folds_screen_at_least_3": bool(sc.get("sgmc_positive_folds", 0) >= SGMC_MIN_POS_FOLDS),
                "sgmc_positive_folds_confirm_at_least_3": (
                    bool(cf.get("sgmc_positive_folds", 0) >= SGMC_MIN_POS_FOLDS) if has_confirm else False
                ),
            }
            promotion[arm] = dict(
                checks,
                confirmation_ran=has_confirm,
                G3_ELIGIBLE=all(checks.values()),
                sgmc=dict(
                    screen=sc.get("sgmc_positive_folds"),
                    confirm=cf.get("sgmc_positive_folds") if has_confirm else None,
                    mean_gain_screen=_sgmc_mean(sc),
                    mean_gain_confirm=_sgmc_mean(cf) if has_confirm else None,
                ),
            )
        gate_path = base / "promotion_gate.json"
        gate_path.write_text(
            json.dumps(
                dict(
                    generated_by="scripts/analyze_h43_screen.py",
                    date="2026-10-03",
                    rule=(
                        "knowledge/27 §4 G1+G2+G3: an arm is G3_ELIGIBLE only if it passes G1 on draws 32/33, "
                        "passes G2 on draws 34/35, exceeds holdout_best (0.14479018210246675) in both stages, and "
                        "gains on the SGMC off-catalogue secondary proxy in >= 3 of 4 folds in both stages."
                    ),
                    holdout_best=HOLDOUT_BEST,
                    arms=promotion,
                ),
                indent=2,
            )
            + "\n"
        )
        print(f"wrote {gate_path}")

    payload = dict(
        generated_by="scripts/analyze_h43_screen.py",
        date="2026-10-03",
        gates=dict(
            mean_gain=MEAN_GAIN,
            min_positive_folds=MIN_POS_FOLDS,
            worst_floor=WORST_FLOOR,
            budget_band=list(BAND),
            sgmc_min_positive_folds=SGMC_MIN_POS_FOLDS,
            holdout_best=HOLDOUT_BEST,
            min_nonzero_fraction=MIN_NONZERO_FRACTION,
        ),
        design_check=design_check,
        note=(
            "Independent recomputation from raw cells only; summary cross-checked. Gate constants copied from "
            "knowledge/27_preregistered_h43_screen_2026-10-03.md §4. DTI here is the catalogue-hidden spatial proxy, "
            "not a competition score."
        ),
        integrity_problems=problems,
        report=report,
    )
    out_path = base / "analyzer_report.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                s: {
                    a: {
                        k: v
                        for k, v in e.items()
                        if k
                        in (
                            "mean_gain",
                            "G1_PASS",
                            "sgmc_gate_pass",
                            "mean_dti",
                            "above_holdout_best",
                            "cells_present",
                            "positive_folds_per_draw",
                            "worst_fold_gain",
                        )
                    }
                    for a, e in r["arms"].items()
                }
                for s, r in report.items()
            },
            indent=2,
        )
    )
    print("problems:", problems if problems else "none")
    print(f"wrote {out_path}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
