#!/usr/bin/env python3
"""H53 screen: cross-scale topographic fabric coherence vs the frozen H34 bar protocol.

Protocol, columns, arms, draws and gates are frozen in
``knowledge/41_preregistered_h53_screen_2026-10-03.md`` BEFORE this script is exercised on real data.
The runner writes that file's SHA-256, the field/module/input hashes and the git state into
``evidence/h53_screen/design.json``, refuses to overwrite existing evidence, requires a clean committed
worktree, never contacts DrivenData, and never reads ``labels.tif`` for anything except the frozen
hide-and-recover draws (via ``gemsdoe.experiment``).

    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h53_screen.py                # both phases
    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h53_screen.py --phase screen # fresh draws 36/37 only
    GEMS_DATA_DIR=$PWD/data python3 scripts/run_h53_screen.py --max-cells 2  # chunked; --resume continues

Phase ``reproduction`` re-fits the two frozen controls on the spent draws 20/21 and compares them with
the stored H34 cells (gate G4); phase ``screen`` fits the five arms on the fresh draws 36/37. Raw rows
are appended to ``cells.jsonl`` (never rewritten); the summary is written only when every declared cell
of the requested phases is present.
"""

from __future__ import annotations

import argparse
import gc
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
from scipy.ndimage import binary_dilation, distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.experiment import HGB_PARAMS, Cell, load_context  # noqa: E402
from gemsdoe.h53 import H53_NAMES  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.thinning import dot_thin, score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "41_preregistered_h53_screen_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "h53_screen"
H34_CELLS = ROOT / "evidence" / "h34_coverage_screen" / "cells.jsonl"
FIELDS = ("h53_fields.npy", "h53_fields.json")
FOLDS = (0, 1, 2, 3)
FOLD_NAMES = ("NW", "NE", "SW", "SE")
SCREEN_DRAWS = (36, 37)
REPRO_DRAWS = (20, 21)
KFRAC = 0.0245
MIN_DIST_PX = 2.4
OFF_CATALOGUE_MIN_PX = 5.0
HOLDOUT_BEST = 0.14479018210246675  # recorded H34 C1_geodesic_dots mean (knowledge/27)
PRIMARY_ARM = "A1_h53_persist"
ARMS = ("C0_base", "C1_geodesic_dots", "A1_h53_persist", "A2_h53_off", "A3_h53_scarp")
REPRO_ARMS = ("C0_base", "C1_geodesic_dots")
GATES = dict(
    primary_arm=PRIMARY_ARM,
    mean_gain=0.005,
    min_positive_folds=3,
    max_fold_loss=-0.010,
    budget_ratio_band=(0.75, 1.25),
    sgmc_min_mean_gain=0.000,
    sgmc_min_positive_folds=3,
    min_nonzero_fraction=0.002,
    min_split_cells_for_feature_arm=3,
    holdout_best=HOLDOUT_BEST,
    reproduction_tolerance=1e-6,
)


def rel(path: Path) -> str:
    """Path relative to the repository when possible, else the absolute path (scratch --out dirs)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "not-installed"


def git_state(ignore_prefix: str | None = None) -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(f"git state unavailable ({exc}); the stage requires a clean committed tree") from exc

    lines = run("status", "--porcelain").splitlines()
    if ignore_prefix:
        lines = [line for line in lines if ignore_prefix not in line]
    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"),
                dirty_worktree=bool(lines))


def sgmc_class(data: Path, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """State-geologic-map faults that are neither catalogue pixels nor within 300 m of one (H34 convention)."""
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as source:
        sgmc = source.read(1) > 0
    near = binary_dilation(labels, iterations=3)
    truth = sgmc & ~labels & ~near
    return truth, dict(sgmc_positive=int(sgmc.sum()), off_catalogue=int(truth.sum()),
                       on_catalogue=int((sgmc & labels).sum()), within_300m=int((sgmc & ~labels & near).sum()))


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


def load_h53(work: Path, foot_shape: tuple[int, int], fi: np.ndarray) -> tuple[np.ndarray, dict]:
    vectors = np.load(work / FIELDS[0], mmap_mode="r")
    if vectors.shape != (len(H53_NAMES), fi.size):
        raise SystemExit(f"cached H53 fields {vectors.shape} do not match the footprint vector {fi.size}")
    meta = json.loads((work / FIELDS[1]).read_text())
    if meta.get("label_free") is not True:
        raise SystemExit("cached H53 fields are not marked label-free; refusing to screen them")
    return np.asarray(vectors), meta


def split_count(model: HistGradientBoostingClassifier, first_feature: int) -> int:
    total = 0
    for tree in getattr(model, "_predictors", []):
        for predictor in tree:
            feats = np.asarray(predictor.nodes["feature_idx"], dtype=np.int64)
            total += int((feats >= first_feature).sum())
    return total


def run_cells(ctx, vectors: np.ndarray, phase: str, folds, draws, arms, sink, sgmc_truth: np.ndarray,
              *, scarp_norm: np.ndarray, resume_done: set, max_cells: int | None = None) -> list[dict]:
    rows: list[dict] = []
    done_cells = 0
    for fold in folds:
        for draw in draws:
            if all((phase, fold, draw, arm) in resume_done for arm in arms):
                continue
            if max_cells is not None and done_cells >= max_cells:
                print(f"stopping after {done_cells} cell(s) in phase {phase}; re-run --resume to continue", flush=True)
                return rows
            done_cells += 1
            t0 = time.time()
            cell = Cell(ctx, fold, draw, extras=True, h27=True)
            k = int(round(KFRAC * cell.dom_c.sum()))
            sl = cell.sl
            # Off-catalogue indicator in the FOOTPRINT-VECTOR space Cell indexes with (full-grid Euclidean
            # distance to the draw's visible catalogue, so the quadrant border does not truncate it).
            off_vec = (distance_transform_edt(~cell.draw.visible) >= OFF_CATALOGUE_MIN_PX).ravel()[ctx.fi]

            # --- base fit (69 frozen columns): C0 and C1 controls ---
            model = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
            t_fit = time.time()
            model.fit(cell.Xtr, cell.y)
            fit_s = time.time() - t_fit
            t_pred = time.time()
            p = model.predict_proba(cell.Xq)[:, 1].astype(np.float32)
            predict_s = time.time() - t_pred
            auc_base = cell.auc(np.nan_to_num(p, nan=0.0))
            del model
            score_crop, candidates = cell.candidates(p, k)
            del p
            emissions = {
                "C0_base": score_ordered_dots(score_crop, candidates, MIN_DIST_PX),
                "C1_geodesic_dots": dot_thin(candidates, MIN_DIST_PX),
            }
            n_candidates = int(candidates.sum())
            del score_crop, candidates

            extra_names = list(H53_NAMES) + [f"{n}_OFF" for n in H53_NAMES] + ["H53_SCARP_X"]
            split_diag: dict[str, dict] = {}
            if any(arm.startswith("A") for arm in arms):
                base_n = cell.Xtr.shape[1]
                h53_vec = {name: vectors[i] for i, name in enumerate(H53_NAMES)}
                extra_vec = {**h53_vec,
                             **{f"{n}_OFF": (h53_vec[n] * off_vec).astype(np.float32) for n in H53_NAMES},
                             "H53_SCARP_X": (h53_vec["H53_PERSIST"] * np.asarray(scarp_norm, np.float32)).astype(np.float32)}
                Xtr = np.concatenate([cell.Xtr] + [extra_vec[n][cell.train_idx][:, None] for n in extra_names], axis=1)
                Xq = np.concatenate([cell.Xq] + [extra_vec[n][cell.q][:, None] for n in extra_names], axis=1)
                del cell.Xtr, cell.Xq
                idx = {n: base_n + i for i, n in enumerate(extra_names)}
                plans = {
                    "A1_h53_persist": [idx[n] for n in H53_NAMES],
                    "A2_h53_off": [idx[f"{n}_OFF"] for n in H53_NAMES],
                    "A3_h53_scarp": [idx["H53_PERSIST"], idx["H53_SCARP_X"]],
                }
                for arm in [a for a in arms if a.startswith("A")]:
                    cols = list(range(base_n)) + plans[arm]
                    m = HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)
                    t_fit = time.time()
                    m.fit(np.ascontiguousarray(Xtr[:, cols]), cell.y)
                    fit_s = time.time() - t_fit
                    t_pred = time.time()
                    p_arm = m.predict_proba(np.ascontiguousarray(Xq[:, cols]))[:, 1].astype(np.float32)
                    predict_s = time.time() - t_pred
                    score_arm, cand_arm = cell.candidates(p_arm, k)
                    emissions[arm] = score_ordered_dots(score_arm, cand_arm, MIN_DIST_PX)
                    split_diag[arm] = dict(h53_splits=split_count(m, first_feature=base_n),
                                           n_features=len(cols), auc=cell.auc(np.nan_to_num(p_arm, nan=0.0)),
                                           fit_s=fit_s, predict_s=predict_s)
                    del m, p_arm, score_arm, cand_arm
                del Xtr, Xq

            for arm in arms:
                emitted = emissions[arm]
                result = cell.evaluate(emitted)
                sg = dti_binary(emitted, sgmc_truth[sl] & cell.dom_c, valid=cell.dom_c, known=cell.known_c)
                row = dict(phase=phase, fold=fold, fold_name=FOLD_NAMES[fold], draw=draw, arm=arm, **result,
                           sgmc_dti=float(sg["dti"]), sgmc_n_truth=int(sg["n_truth"]),
                           identical_to_c1=bool(np.array_equal(emitted, emissions["C1_geodesic_dots"])),
                           k=k, n_candidates=n_candidates)
                if arm in REPRO_ARMS:
                    row.update(fit_s=fit_s, predict_s=predict_s, auc=auc_base)
                else:
                    row["feature_diag"] = split_diag.get(arm)
                    row["auc"] = split_diag.get(arm, {}).get("auc", float("nan"))
                if arm == PRIMARY_ARM:
                    dom_q = cell.domain.ravel()[ctx.fi][cell.q]
                    row["off_catalogue_fraction"] = float(np.mean(off_vec[cell.q][dom_q]))
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            del emissions, cell
            gc.collect()
            brief = " ".join(
                f"{a.split('_')[0]}={row['dti']:.4f}"
                for a in arms
                for row in [next((r for r in reversed(rows)
                                  if r["fold"] == fold and r["draw"] == draw and r["arm"] == a), None)]
                if row is not None)
            print(f"phase={phase} fold={FOLD_NAMES[fold]} draw={draw} {brief} ({time.time() - t0:.0f}s)", flush=True)
    return rows


def open_cells(path: Path, resume: bool) -> tuple[list[dict], set]:
    rows: list[dict] = []
    done: set = set()
    if path.is_file() and resume:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rows.append(row)
            done.add((row["phase"], int(row["fold"]), int(row["draw"]), row["arm"]))
    return rows, done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=EVIDENCE)
    parser.add_argument("--phase", choices=("all", "reproduction", "screen"), default="all")
    parser.add_argument("--resume", action="store_true", help="append to an existing cells.jsonl")
    parser.add_argument("--max-cells", type=int, default=None)
    args = parser.parse_args()

    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    cells_path, design_path, summary_path = out / "cells.jsonl", out / "design.json", out / "summary.json"
    if args.resume:
        for path in (summary_path,):
            if path.exists():
                raise SystemExit(f"refusing to overwrite existing evidence: {path}")
    else:
        for path in (design_path, cells_path, summary_path):
            if path.exists():
                raise SystemExit(f"refusing to overwrite existing evidence in {out} (use --resume)")

    state = git_state(ignore_prefix="evidence/h53_screen")
    if state["dirty_worktree"]:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data, work = data_dir(), work_dir()
    missing = [str(p) for p in (data / "labels.tif", data / "sample_submission.tif",
                                data / "external" / "derived_sgmc_faults_100m_u8.tif") if not p.is_file()]
    missing += [str(work / name) for name in ("static_ABCD.npy", "addons.npy", *FIELDS) if not (work / name).is_file()]
    if missing:
        raise SystemExit(f"missing inputs/caches: {missing} (run prepare_data.py, build_features.py, "
                         f"build_addons.py, build_h53_fields.py first)")
    stored = stored_h34_controls()
    if not stored:
        raise SystemExit("missing evidence/h34_coverage_screen/cells.jsonl; gate G4 cannot be evaluated")

    ctx = load_context(work)
    vectors, field_meta = load_h53(work, ctx.foot.shape, ctx.fi)
    sgmc_truth, sgmc_stats = sgmc_class(data, ctx.labels)
    scarp_norm = np.zeros(ctx.fi.size, np.float32)
    if ctx.h27_scarp is not None:
        scarp_norm = np.asarray(ctx.h27_scarp, np.float32)
    scarp_p01, scarp_p99 = float(np.min(scarp_norm)), float(np.max(scarp_norm))

    if args.resume and design_path.is_file():
        design = json.loads(design_path.read_text())
        if design["preregistration"]["sha256"] != sha256_file(PREREG):
            raise SystemExit("frozen preregistration changed since design.json was written; refusing to resume")
    else:
        design = dict(
            stage="h53_screen",
            experiment="H53 cross-scale topographic fabric coherence, on the frozen H34 bar protocol",
            preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
            folds=list(FOLD_NAMES), screen_draws=list(SCREEN_DRAWS), reproduction_draws=list(REPRO_DRAWS),
            arms=list(ARMS), reproduction_arms=list(REPRO_ARMS), primary_arm=PRIMARY_ARM, gates=GATES,
            constants=dict(k_frac=KFRAC, min_dist_px=MIN_DIST_PX, off_catalogue_min_px=OFF_CATALOGUE_MIN_PX,
                           emit_C0="score_ordered_dots(score_crop, candidates, 2.4)",
                           emit_C1="dot_thin(candidates, 2.4)",
                           arm_columns=dict(A1_h53_persist=list(H53_NAMES),
                                            A2_h53_off=[f"{n}_OFF" for n in H53_NAMES],
                                            A3_h53_scarp=["H53_PERSIST", "H53_SCARP_X"])),
            h53_fields=dict(config=field_meta["config"], diagnostics=field_meta["diagnostics"],
                            cache_sha256={name: sha256_file(work / name) for name in FIELDS},
                            scarp_normalisation=dict(p01=scarp_p01, p99=scarp_p99)),
            sgmc=sgmc_stats,
            draw_seed_inventory=dict(used_before="0-15, 20-35 (registry/draw_ledger.json)",
                                     screen=list(SCREEN_DRAWS), reproduction=list(REPRO_DRAWS),
                                     note="screen draws 36/37 are claimed by this stage; draws 20/21 are reused only "
                                          "for the G4 control-reproduction check"),
            environment=dict(python=platform.python_version(), numpy=np.__version__,
                             scikit_learn=package_version("scikit-learn"), scipy=package_version("scipy"),
                             rasterio=package_version("rasterio"), platform=platform.platform()),
            modules={p: sha256_file(ROOT / p) for p in ("src/gemsdoe/h53.py", "src/gemsdoe/experiment.py",
                                                        "src/gemsdoe/thinning.py", "src/gemsdoe/metric.py",
                                                        "scripts/run_h53_screen.py")},
            git=state, drivendata_contacted=False,
            started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        design_path.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")
        print(f"design frozen: {rel(design_path)} (prereg sha256 "
              f"{design['preregistration']['sha256'][:12]}…)")

    rows, done = open_cells(cells_path, args.resume)
    mode = "a" if args.resume else "w"
    t0 = time.time()
    with cells_path.open(mode) as sink:
        if args.phase in ("all", "reproduction"):
            rows += run_cells(ctx, vectors, "reproduction", FOLDS, REPRO_DRAWS, REPRO_ARMS, sink, sgmc_truth,
                              scarp_norm=scarp_norm, resume_done=done, max_cells=args.max_cells)
        if args.phase in ("all", "screen"):
            rows += run_cells(ctx, vectors, "screen", FOLDS, SCREEN_DRAWS, ARMS, sink, sgmc_truth,
                              scarp_norm=scarp_norm, resume_done=done,
                              max_cells=None if args.phase == "screen" else args.max_cells)
    print(f"phase rows written: {len(rows)} in {time.time() - t0:.0f}s; run "
          f"`python3 scripts/analyze_h53_screen.py` for the gates", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
