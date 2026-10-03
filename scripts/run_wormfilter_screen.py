#!/usr/bin/env python3
"""H52 stage: does worming survival used as an *emission filter* clear the recorded slot bar?

Protocol, arms and gates are frozen in ``knowledge/37_preregistered_wormfilter_h34protocol_2026-10-03.md``
BEFORE this script runs. The runner records that file's SHA-256, the input/cache/module hashes and the
git state into ``evidence/wormfilter_screen/design.json``, refuses to overwrite existing evidence,
requires a clean committed worktree, and never contacts DrivenData.

    python3 scripts/build_wormfilter_fields.py   # label-free fields (cached)
    python3 scripts/run_wormfilter_screen.py

Seven arms on each of the 8 cells (4 folds x draws 20/21): the two frozen H34 controls, the declared
primary ``W2_surv_refill`` (shallow-only veto + refill + 2.4 px dotting), three secondary veto arms and
the feature-role comparator ``W5_surv_features``. The stored H34 control values are re-read from
``evidence/h34_coverage_screen/cells.jsonl`` and their reproduction is gate G4.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import Cell, HGB_PARAMS, load_context  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import dot_thin, ridge_nms, score_ordered_dots, select_top_positive  # noqa: E402
from gemsdoe.wormfilter import WF_NAMES, WormFilterConfig, azimuth_veto, shallow_veto  # noqa: E402

PREREG = ROOT / "knowledge" / "37_preregistered_wormfilter_h34protocol_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "wormfilter_screen"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
FIELDS = ("wormfilter_fields.npy", "wormfilter_az_defined.npy", "wormfilter_fields.json")
D28_INPUT = "inputs/dotted_h19_5_d2_8_nan.tif"
FOLDS = (0, 1, 2, 3)
FOLD_NAMES = ("NW", "NE", "SW", "SE")
DRAWS = (20, 21)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
HOLDOUT_BEST = 0.14479018210246675  # recorded H34 C1_geodesic_dots mean (knowledge/27)
PRIMARY_ARM = "W2_surv_refill"
ARMS = ("C0_base", "C1_geodesic_dots", "W1_surv_veto", "W2_surv_refill",
        "W3_azimuth_refill", "W4_union_refill", "W5_surv_features")
GATES = dict(
    primary_arm=PRIMARY_ARM,
    mean_gain=0.005,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    budget_ratio_band=(0.75, 1.25),
    sgmc_min_mean_gain=0.000,
    sgmc_min_positive_folds=3,
    veto_rate_band=(0.02, 0.60),
    min_split_cells_for_feature_arm=3,
    holdout_best=HOLDOUT_BEST,
    reproduction_tolerance=1e-6,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(f"git state unavailable ({exc}); the stage requires a clean committed tree") from exc

    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"),
                dirty_worktree=bool(run("status", "--porcelain")))


def sgmc_class(data: Path, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """State-geologic-map faults that are neither catalogue pixels nor within 300 m of one (H34 convention)."""
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as source:
        sgmc = source.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    truth = sgmc & ~labels & ~near
    return truth, dict(
        sgmc_positive=int(sgmc.sum()), off_catalogue=int(truth.sum()),
        on_catalogue=int((sgmc & labels).sum()), within_300m=int((sgmc & ~labels & near).sum()),
    )


def stored_h34_controls() -> dict[tuple[str, int, str], float]:
    out: dict[tuple[str, int, str], float] = {}
    if not H34_CELLS.is_file():
        return out
    for line in H34_CELLS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["arm"] in ("C0_ordered_dots", "C1_geodesic_dots"):
            out[(row["fold_name"], int(row["draw"]), row["arm"])] = float(row["dti"])
    return out


def load_fields(work: Path, foot_shape: tuple[int, int], fi: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load the cached label-free worm fields as (vectors, grids)."""
    vectors = np.load(work / FIELDS[0], mmap_mode="r")
    az_defined = np.load(work / FIELDS[1], mmap_mode="r")
    if vectors.shape != (len(WF_NAMES), fi.size):
        raise SystemExit(f"cached worm fields {vectors.shape} do not match the footprint vector {fi.size}")
    if az_defined.shape != (fi.size,):
        raise SystemExit("cached azimuth-defined vector does not match the footprint vector")
    grids: dict[str, np.ndarray] = {}
    for name in ("WF_SHALLOW_ONLY", "WF_AZ_AGREE"):
        grid = np.zeros(foot_shape, np.float32)
        grid.ravel()[fi] = np.asarray(vectors[WF_NAMES.index(name)])
        grids[name] = grid
    grid = np.zeros(foot_shape, np.float32)
    grid.ravel()[fi] = np.asarray(az_defined)
    grids["WF_AZ_DEFINED"] = grid
    return np.asarray(vectors), grids


def refill(cell: Cell, score_crop: np.ndarray, ridge: np.ndarray, veto: np.ndarray, k: int) -> np.ndarray:
    """Top-k ridge candidates outside the veto and the visible catalogue, then the frozen dotting."""
    eligible = ridge & ~cell.known_c & ~veto
    top = select_top_positive(score_crop, eligible, k)
    return dot_thin(top, MIN_DIST_PX)


def artifact_audit(grids: dict[str, np.ndarray], fi: np.ndarray, data: Path, surv_grid: np.ndarray) -> dict:
    """Label-free numbers: how much of each reference emission the shallow-only flag rejects."""
    out: dict = dict(
        footprint_shallow_fraction=float(np.mean(grids["WF_SHALLOW_ONLY"].ravel()[fi] > 0.5)),
        footprint_mean_surv_joint=float(np.mean(np.asarray(surv_grid).ravel()[fi])),
        azimuth_defined_fraction=float(np.mean(grids["WF_AZ_DEFINED"].ravel()[fi] > 0.5)),
    )
    d28 = data / D28_INPUT
    if d28.is_file():
        with rasterio.open(d28) as source:
            band = source.read(1)
        emission = np.isfinite(band) & (np.nan_to_num(band, nan=0.0) > 0)
        del band
        n = int(emission.sum())
        out["d28_reference"] = dict(
            file=str(d28.relative_to(ROOT)), emitted_px=n,
            flagged_shallow=int((emission & (grids["WF_SHALLOW_ONLY"] > 0.5)).sum()),
            flagged_fraction=float((emission & (grids["WF_SHALLOW_ONLY"] > 0.5)).sum() / max(n, 1)),
            mean_surv_joint_on_dots=float(np.asarray(surv_grid)[emission].mean()) if n else None,
        )
    return out


def run_cells(ctx, vectors: np.ndarray, grids: dict[str, np.ndarray], surv_grid: np.ndarray,
              sink, sgmc_truth: np.ndarray) -> list[dict]:
    rows: list[dict] = []
    for fold in FOLDS:
        for draw in DRAWS:
            t0 = time.time()
            cell = Cell(ctx, fold, draw, extras=True, h27=True)
            base_n = cell.Xtr.shape[1]
            k = int(round(KFRAC * cell.dom_c.sum()))
            sl = cell.sl
            shallow_crop = grids["WF_SHALLOW_ONLY"][sl] > 0.5
            az_crop = grids["WF_AZ_AGREE"][sl]
            azdef_crop = grids["WF_AZ_DEFINED"][sl]

            # --- fit 1: the frozen control matrix (six of the seven arms share this score field) ---
            model = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
            t_fit = time.time()
            model.fit(cell.Xtr, cell.y)
            fit_s = time.time() - t_fit
            t_pred = time.time()
            p = model.predict_proba(np.ascontiguousarray(cell.Xq))[:, 1].astype(np.float32)
            predict_s = time.time() - t_pred
            auc_base = cell.auc(np.nan_to_num(p, nan=0.0))

            score_crop, candidates = cell.candidates(p, k)
            # Recompute the ridge mask so the refill arms see exactly the C1 candidate rule minus the veto.
            ridge = ridge_nms(score_crop, cell.dom_c, 1.0)
            veto_shallow = shallow_veto(candidates, shallow_crop.astype(np.float32))
            veto_az = azimuth_veto(candidates, az_crop, azdef_crop, WormFilterConfig().tau_azimuth)
            veto_union = veto_shallow | veto_az
            n_cand = int(candidates.sum())

            emissions = {
                "C0_base": score_ordered_dots(score_crop, candidates, MIN_DIST_PX),
                "C1_geodesic_dots": dot_thin(candidates, MIN_DIST_PX),
                "W1_surv_veto": dot_thin(candidates & ~veto_shallow, MIN_DIST_PX),
                "W2_surv_refill": refill(cell, score_crop, ridge, veto_shallow, k),
                "W3_azimuth_refill": refill(cell, score_crop, ridge, veto_az, k),
                "W4_union_refill": refill(cell, score_crop, ridge, veto_union, k),
            }
            veto_stats = dict(
                candidates=n_cand,
                veto_shallow_rate=float(veto_shallow.sum() / max(n_cand, 1)),
                veto_azimuth_rate=float(veto_az.sum() / max(n_cand, 1)),
                veto_union_rate=float(veto_union.sum() / max(n_cand, 1)),
                shallow_fraction_in_domain=float(np.mean(shallow_crop[cell.dom_c])),
                mean_surv_joint_in_domain=float(np.mean(surv_grid[sl][cell.dom_c])),
            )

            # --- fit 2: the feature-role comparator (same emission as C0, 8 extra columns) ---
            Xtr_w = np.concatenate([cell.Xtr] + [vectors[i][cell.train_idx][:, None] for i in range(len(WF_NAMES))], axis=1)
            Xq_w = np.concatenate([cell.Xq] + [vectors[i][cell.q][:, None] for i in range(len(WF_NAMES))], axis=1)
            all_cols = list(range(base_n + len(WF_NAMES)))
            model_w = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
            t_fit = time.time()
            model_w.fit(np.ascontiguousarray(Xtr_w[:, all_cols]), cell.y)
            fit_w = time.time() - t_fit
            t_pred = time.time()
            p_w = model_w.predict_proba(np.ascontiguousarray(Xq_w[:, all_cols]))[:, 1].astype(np.float32)
            predict_w = time.time() - t_pred
            del Xtr_w, Xq_w
            score_w, cand_w = cell.candidates(p_w, k)
            emissions["W5_surv_features"] = score_ordered_dots(score_w, cand_w, MIN_DIST_PX)
            # Split accounting on the WF block (gate G6): only feature indices >= base_n count.
            # Leaves carry feature_idx = -2, so they can never be counted as WF splits.
            wf_splits = 0
            for tree in getattr(model_w, "_predictors", []):
                for predictor in tree:
                    feats = np.asarray(predictor.nodes["feature_idx"], dtype=np.int64)
                    wf_splits += int((feats >= base_n).sum())
            feature_diag = dict(wf_splits=int(wf_splits), n_features=len(all_cols), auc=cell.auc(np.nan_to_num(p_w, nan=0.0)))

            timing = dict(fit_s=fit_s, predict_s=predict_s)
            for arm in ARMS:
                emitted = emissions[arm]
                result = cell.evaluate(emitted)
                sg = dti_binary(emitted, sgmc_truth[sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                identical_to_c1 = bool(np.array_equal(emitted, emissions["C1_geodesic_dots"]))
                row = dict(fold=fold, fold_name=FOLD_NAMES[fold], draw=draw, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]),
                           identical_to_c1=identical_to_c1,
                           auc=feature_diag["auc"] if arm == "W5_surv_features" else auc_base,
                           **timing)
                if arm == PRIMARY_ARM:
                    row["veto"] = veto_stats
                if arm == "W5_surv_features":
                    row["feature_diag"] = dict(feature_diag, fit_s=fit_w, predict_s=predict_w)
                if arm == "C0_base":
                    row["n_candidates"] = n_cand
                    row["k"] = k
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            brief = " ".join(f"{a.split('_')[0]}={next(r['dti'] for r in rows if r['fold'] == fold and r['draw'] == draw and r['arm'] == a):.4f}"
                             for a in ARMS)
            print(f"fold={FOLD_NAMES[fold]} draw={draw} {brief} "
                  f"veto={veto_stats['veto_shallow_rate']:.3f} ({time.time() - t0:.0f}s)", flush=True)
    return rows


def gate_summary(rows: list[dict], stored: dict) -> dict:
    def mean(field: str, arm: str, fold: int | None = None) -> float:
        vals = [r[field] for r in rows if r["arm"] == arm and (fold is None or r["fold"] == fold)]
        return float(np.mean(vals)) if vals else float("nan")

    control_means = {fold: max(mean("dti", "C0_base", fold), mean("dti", "C1_geodesic_dots", fold)) for fold in FOLDS}
    gains = [mean("dti", PRIMARY_ARM, fold) - control_means[fold] for fold in FOLDS]
    sgmc_gains = [mean("sgmc_dti", PRIMARY_ARM, fold)
                  - max(mean("sgmc_dti", "C0_base", fold), mean("sgmc_dti", "C1_geodesic_dots", fold))
                  for fold in FOLDS]

    veto_rates = [r["veto"]["veto_shallow_rate"] for r in rows if r["arm"] == PRIMARY_ARM]
    mean_veto = float(np.mean(veto_rates)) if veto_rates else float("nan")
    identical_cells = int(sum(r["identical_to_c1"] for r in rows if r["arm"] == PRIMARY_ARM))
    expected_cells = len(FOLDS) * len(DRAWS)

    budget_ratios = []
    for fold in FOLDS:
        for draw in DRAWS:
            arm_rows = [r for r in rows if r["arm"] == PRIMARY_ARM and r["fold"] == fold and r["draw"] == draw]
            c1_rows = [r for r in rows if r["arm"] == "C1_geodesic_dots" and r["fold"] == fold and r["draw"] == draw]
            if arm_rows and c1_rows:
                budget_ratios.append(arm_rows[0]["emitted"] / max(c1_rows[0]["emitted"], 1))
    lo, hi = GATES["budget_ratio_band"]
    budget_ok = bool(budget_ratios and all(lo <= ratio <= hi for ratio in budget_ratios))

    reproduction = []
    for row in rows:
        if row["arm"] in ("C0_base", "C1_geodesic_dots"):
            key = (row["fold_name"], row["draw"], "C0_ordered_dots" if row["arm"] == "C0_base" else row["arm"])
            if key in stored:
                reproduction.append(dict(fold_name=row["fold_name"], draw=row["draw"], arm=row["arm"],
                                         rebuilt=float(row["dti"]), stored=float(stored[key]),
                                         delta=float(row["dti"]) - float(stored[key])))
    repro_max = max((abs(item["delta"]) for item in reproduction), default=float("nan"))

    wf_split_cells = int(sum(1 for r in rows if r["arm"] == "W5_surv_features"
                             and r.get("feature_diag", {}).get("wf_splits", 0) > 0))

    mean_gain = float(np.mean(gains))
    primary_mean = mean("dti", PRIMARY_ARM)
    veto_lo, veto_hi = GATES["veto_rate_band"]
    gates = dict(
        mean_gain=mean_gain, fold_gains=gains, worst_fold=float(np.min(gains)),
        positive_folds=int(sum(g > 0 for g in gains)), budget_ok=budget_ok,
        budget_ratio_min=float(np.min(budget_ratios)) if budget_ratios else None,
        budget_ratio_max=float(np.max(budget_ratios)) if budget_ratios else None,
        primary_mean_dti=primary_mean, bar_mean=max(control_means.values()), bar_from_stored=HOLDOUT_BEST,
        sgmc_mean_gain=float(np.mean(sgmc_gains)), sgmc_fold_gains=sgmc_gains,
        sgmc_positive_folds=int(sum(g > 0 for g in sgmc_gains)),
        mean_veto_rate=mean_veto, veto_rates=veto_rates,
        identical_to_c1_cells=identical_cells, expected_cells=expected_cells,
        wf_split_cells=wf_split_cells,
        cells_present=bool(len(rows) == expected_cells * len(ARMS)),
        all_finite=bool(all(np.isfinite(r["dti"]) for r in rows)),
        reproduction_max_abs_delta=repro_max, reproduction_cells=reproduction,
    )
    g1 = bool(mean_gain >= GATES["mean_gain"] and gates["positive_folds"] >= GATES["min_positive_folds"]
              and gates["worst_fold"] >= GATES["max_fold_loss"] and budget_ok)
    g2 = bool(primary_mean > GATES["holdout_best"])
    g3 = bool(gates["sgmc_mean_gain"] >= GATES["sgmc_min_mean_gain"]
              and gates["sgmc_positive_folds"] >= GATES["sgmc_min_positive_folds"])
    g4 = bool(gates["cells_present"] and gates["all_finite"] and np.isfinite(repro_max)
              and repro_max <= GATES["reproduction_tolerance"])
    g5 = bool(identical_cells < expected_cells and veto_lo <= mean_veto <= veto_hi)
    g6 = bool(wf_split_cells >= GATES["min_split_cells_for_feature_arm"])
    if not g4:
        verdict = "NOT COMPARABLE: the frozen controls did not reproduce the stored H34 cells; no verdict is issued."
    elif not g5:
        verdict = ("FAIL-INERT: the veto either changed nothing or changed the budget instead of the ranking "
                   "(G5); no promotion and no claim about the filter role.")
    elif g1 and g2 and g3:
        verdict = "SLOT-ELIGIBLE by the frozen rule: a cross-fitted candidate artifact may be built for owner review."
    elif g1 and g2 and not g3:
        verdict = "PRIMARY PASS, SECONDARY-PROXY CONFLICT: no promotion (the H41 outcome)."
    else:
        verdict = "NO PROMOTION: worming survival as an emission filter does not clear the frozen gates on the bar protocol."
    return dict(arms={arm: mean("dti", arm) for arm in ARMS}, controls=control_means, gates=gates,
                gate_checks=dict(G1=g1, G2=g2, G3=g3, G4=g4, G5=g5, G6=g6), verdict=verdict)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    out = args.out
    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    out.mkdir(parents=True, exist_ok=True)
    cells_path, design_path, summary_path = out / "cells.jsonl", out / "design.json", out / "summary.json"
    if design_path.exists() or cells_path.exists() or summary_path.exists():
        raise SystemExit(f"refusing to overwrite existing evidence in {out}")

    state = git_state()
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    missing = [str(p) for p in (data / "labels.tif", data / "sample_submission.tif",
                                data / "external" / "derived_sgmc_faults_100m_u8.tif") if not p.is_file()]
    missing += [str(work / name) for name in ("static_ABCD.npy", "addons.npy", *FIELDS) if not (work / name).is_file()]
    if missing:
        raise SystemExit(f"missing inputs/caches: {missing} (run prepare_data.py, build_features.py, "
                         f"build_addons.py, build_wormfilter_fields.py first)")

    stored = stored_h34_controls()
    if not stored:
        raise SystemExit("missing evidence/h34_coverage_screen/cells.jsonl; gate G4 cannot be evaluated")

    ctx = load_context(work)
    vectors, grids = load_fields(work, ctx.foot.shape, ctx.fi)
    surv_grid = np.zeros(ctx.foot.shape, np.float32)
    surv_grid.ravel()[ctx.fi] = vectors[WF_NAMES.index("WF_SURV_JOINT")]
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)
    audit = artifact_audit(grids, ctx.fi, data, surv_grid)
    field_meta = json.loads((work / FIELDS[2]).read_text())

    design = dict(
        stage="wormfilter_screen", experiment="H52 worming survival as an emission filter, on the H34 bar protocol",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        folds=[FOLD_NAMES[f] for f in FOLDS], draws=list(DRAWS), arms=list(ARMS), primary_arm=PRIMARY_ARM,
        gates=GATES,
        constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX,
                       emit_C0="score_ordered_dots(score_crop, candidates, 2.4)",
                       emit_C1="dot_thin(candidates, 2.4)",
                       refill="select_top_positive(score, ridge & ~known & ~veto, k) then dot_thin(2.4)"),
        worm_fields=dict(config=field_meta["config"], ladder=field_meta["ladder"],
                         level_detector=field_meta["level_detector"], survival_rule=field_meta["survival_rule"],
                         magnetic_edge_counts=field_meta["diagnostics"]["magnetic"]["edge_counts"],
                         gravity_edge_counts=field_meta["diagnostics"]["gravity"]["edge_counts"],
                         nonzero_fraction=field_meta["diagnostics"]["nonzero_fraction"],
                         mean=field_meta["diagnostics"]["mean"],
                         cache_sha256={name: sha256_file(work / name) for name in FIELDS}),
        artifact_audit=audit,
        sgmc=sgmc_stats,
        draw_seed_inventory=dict(used_before="0-15, 20-25, 28-35 (registry/draw_ledger.json)",
                                 this_stage=list(DRAWS),
                                 note="spent draws reused for a paired comparison against the bar they define; "
                                      "next_free_draw stays 36"),
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         scikit_learn=package_version("scikit-learn"), scipy=package_version("scipy"),
                         rasterio=package_version("rasterio"), platform=platform.platform()),
        modules={p: sha256_file(ROOT / p) for p in ("src/gemsdoe/wormfilter.py", "src/gemsdoe/worms.py",
                                                    "src/gemsdoe/experiment.py", "src/gemsdoe/thinning.py",
                                                    "src/gemsdoe/metric.py", "scripts/run_wormfilter_screen.py")},
        git=state, drivendata_contacted=False, started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    design_path.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")
    print(f"design frozen: {design_path.relative_to(ROOT)} (prereg sha256 {design['preregistration']['sha256'][:12]}…)")
    print("artifact audit: " + json.dumps(audit, indent=None)[:600], flush=True)

    t0 = time.time()
    with cells_path.open("w") as sink:
        rows = run_cells(ctx, vectors, grids, surv_grid, sink, sgmc_truth)
    summary = gate_summary(rows, stored)
    summary["elapsed_s"] = round(time.time() - t0, 1)
    summary["cells"] = len(rows)
    summary["artifact_audit"] = audit
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["gate_checks"], sort_keys=True))
    print(f"arms: {json.dumps({k: round(v, 5) for k, v in summary['arms'].items()})}")
    print(f"mean gain {summary['gates']['mean_gain']:+.6f} | primary mean {summary['gates']['primary_mean_dti']:.5f} "
          f"| bar {HOLDOUT_BEST:.5f} | veto {summary['gates']['mean_veto_rate']:.3f}")
    print(summary["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
