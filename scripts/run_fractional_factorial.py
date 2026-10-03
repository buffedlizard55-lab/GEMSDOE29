#!/usr/bin/env python3
"""Run the frozen 2^(5-1) resolution V fractional factorial over the five feature families.

Design and analysis rules are frozen in
``knowledge/12_preregistered_factorial_families_2026-10-03.md`` (written before the first fit).
Writes ``design.json``, ``cells.jsonl`` (every run x fold x draw response) and ``effects.json``
into ``--out`` and refuses to overwrite an existing run.

    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python scripts/run_fractional_factorial.py --draws 14 15 --folds 0 1 2 3
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import Cell, load_context  # noqa: E402
from gemsdoe.families import family_columns  # noqa: E402
from gemsdoe.paths import work_dir  # noqa: E402

FACTORS = ("A", "B", "C", "D", "E")
TERMS = list(FACTORS) + [f"{a}{b}" for a, b in itertools.combinations(FACTORS, 2)]
ORDER_SEED = 20261003
FIT_SEED = 0
MIN_EFFECT = 0.001
MAX_CELL_LOSS = -0.010
MIN_SIGN_AGREEMENT = 6


def design_runs() -> list[dict]:
    """16 runs, generator E = A*B*C*D (defining relation I = ABCDE), resolution V."""
    runs = []
    for a, b, c, d in itertools.product((1, -1), repeat=4):
        levels = {"A": a, "B": b, "C": c, "D": d, "E": a * b * c * d}
        code = "".join(f if levels[f] > 0 else f.lower() for f in FACTORS)
        runs.append(dict(id=f"run{len(runs):02d}_{code}", levels=levels))
    return runs


def term_contrast(run: dict, name: str) -> int:
    lv = run["levels"]
    if len(name) == 1:
        return int(lv[name])
    return int(lv[name[0]] * lv[name[1]])


def family_column_indices(ctx) -> dict[str, list[int]]:
    idx: dict[str, list[int]] = {f: [] for f in FACTORS}
    for f in "ABCD":
        for name in family_columns(f):
            if name not in ctx.col:
                raise SystemExit(f"family {f} column {name!r} is not present in the context")
            idx[f].append(ctx.col[name])
    for name in ctx.e_names:
        idx["E"].append(ctx.col[name])
    return idx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "factorial_families"))
    ap.add_argument("--draws", type=int, nargs="+", default=[14, 15])
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2, 3])
    args = ap.parse_args()

    out = Path(args.out)
    if (out / "design.json").exists() or (out / "cells.jsonl").exists() or (out / "effects.json").exists():
        raise SystemExit(f"refusing to overwrite an existing factorial run in {out}; choose a fresh --out")
    out.mkdir(parents=True, exist_ok=True)

    runs = design_runs()
    order = [int(i) for i in np.random.default_rng(ORDER_SEED).permutation(len(runs))]
    design = dict(
        experiment="2^(5-1) resolution V fractional factorial over feature families A-E",
        preregistration="knowledge/12_preregistered_factorial_families_2026-10-03.md",
        generator="E = A*B*C*D",
        runs=runs,
        run_order=[runs[i]["id"] for i in order],
        order_seed=ORDER_SEED,
        fit_seed=FIT_SEED,
        contrasts=TERMS,
        response="masked hide-and-recover holdout DTI via Cell.evaluate on the standard screen emission",
        emission="cell.emit: ridge NMS -> drop known -> top K=0.0245*domain -> dot_thin(1.5)",
        draws=list(args.draws),
        folds=list(args.folds),
        analysis=dict(
            estimator="per-cell (fold, draw) paired contrast mean(+1) - mean(-1) for each term",
            se="sample standard deviation of the 8 cell contrasts / sqrt(8), Student t on 7 df",
            support_rule=dict(min_abs_effect=MIN_EFFECT, min_sign_agreement=MIN_SIGN_AGREEMENT,
                              n_cells=8, max_cell_loss=MAX_CELL_LOSS),
            note="the 16-run design is saturated, so error comes from fold-block replication, not from "
                 "unused design columns",
        ),
    )
    (out / "design.json").write_text(json.dumps(design, indent=2) + "\n")
    print(f"design: {len(runs)} runs; folds={args.folds} draws={args.draws}")

    ctx = load_context(work_dir())
    fam_idx = family_column_indices(ctx)
    print("family column counts:", {f: len(v) for f, v in fam_idx.items()})

    rows: list[dict] = []
    t_start = time.time()
    for draw in args.draws:
        for fold in args.folds:
            t0 = time.time()
            cell = Cell(ctx, fold=fold, seed=draw)
            for i in order:
                run = runs[i]
                cols = sorted(j for f in FACTORS if run["levels"][f] > 0 for j in fam_idx[f])
                p, diag = cell.fit_predict(cols, seed=FIT_SEED)
                emitted, _top = cell.emit(p)
                res = cell.evaluate(emitted)
                rows.append(dict(
                    run=run["id"], levels=run["levels"], draw=draw, fold=fold, n_cols=len(cols),
                    dti=res["dti"], coverage=res["coverage"], emitted=res["emitted"], hug=res["hug"],
                    fit_s=diag["fit_s"], predict_s=diag["predict_s"],
                ))
                print(f"draw={draw} fold={fold} {run['id']} cols={len(cols):3d} dti={res['dti']:.5f} "
                      f"cov={res['coverage']:.3f} emit={res['emitted']} ({diag['fit_s']:.1f}s)", flush=True)
            del cell
            print(f"  cell draw={draw} fold={fold} done in {time.time() - t0:.1f}s", flush=True)
    with (out / "cells.jsonl").open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    lookup = {(row["draw"], row["fold"], row["run"]): row["dti"] for row in rows}
    effects = {}
    for name in TERMS:
        cells = []
        for draw in args.draws:
            for fold in args.folds:
                plus = [lookup[(draw, fold, r["id"])] for r in runs if term_contrast(r, name) > 0]
                minus = [lookup[(draw, fold, r["id"])] for r in runs if term_contrast(r, name) < 0]
                cells.append(float(np.mean(plus) - np.mean(minus)))
        a = np.asarray(cells)
        mean = float(a.mean())
        se = float(a.std(ddof=1) / np.sqrt(a.size)) if a.size > 1 else float("nan")
        positive = int((a > 0).sum())
        agreement = max(positive, a.size - positive)
        effects[name] = dict(
            effect=mean, se=se, t=(mean / se if se and np.isfinite(se) and se > 0 else None),
            df=a.size - 1, n_cells=int(a.size), cells=[float(v) for v in a],
            cells_positive=positive, min_cell=float(a.min()),
            supported=bool(abs(mean) >= MIN_EFFECT and a.size == 8 and agreement >= MIN_SIGN_AGREEMENT
                           and float(a.min()) >= MAX_CELL_LOSS),
        )
    summary = dict(
        runtime_s=time.time() - t_start,
        run_means={r["id"]: float(np.mean([row["dti"] for row in rows if row["run"] == r["id"]])) for r in runs},
        grand_mean=float(np.mean([row["dti"] for row in rows])),
        effects=effects,
        supported=[k for k, v in effects.items() if v["supported"]],
        note="family-inclusion effects under the frozen HGB + standard-emission configuration; proxy DTI, "
             "not a competition score; cannot justify a submission slot",
    )
    (out / "effects.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("run_means", "effects")}, indent=2))
    print("supported:", summary["supported"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
