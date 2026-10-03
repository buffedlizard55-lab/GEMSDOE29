#!/usr/bin/env python3
"""Frozen emission-density sweep on the H19-5 habitat (preregistered in ``knowledge/27``).

The sweep re-spaces one *fixed* binary habitat — the owner-mirrored H19-5 emission whose thinned
descendants are the group's best-reported live scores (0.2477 at d = 1.5 px, 0.2600 at d = 2.8 px) — and
scores every spacing on the two registered spatial proxies. It fits nothing, spends no holdout draw, and
never contacts DrivenData; every byte it reads is a hash-pinned owner mirror restored under
``GEMS_DATA_DIR``.

    GEMS_DATA_DIR=$PWD/data python3 scripts/run_emission_sweep.py

Refuses to overwrite existing evidence, and (like the H41 runner) refuses to run from a dirty worktree so
that the preregistration hash it records is the hash of a committed file. The decision rule — including the
rule that a boundary optimum is reported and *not* extended — is frozen in ``knowledge/27`` §5.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.proxies import load_proxy_context, paired_catalogue_hidden, read_binary, score_mask  # noqa: E402
from gemsdoe.thinning import dot_thin, neighbour_profile, score_ordered_dots  # noqa: E402

PREREG = ROOT / "knowledge" / "27_preregistered_emission_density_sweep_2026-10-03.md"
EVIDENCE = ROOT / "evidence" / "emission_sweep"

# ---- frozen specification (knowledge/27 §3) ----------------------------------------------------------
THIN_SPACINGS = (2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 4.8, 5.6, 6.4)
AWARE_SPACINGS = (2.8, 3.6, 4.8)
AWARE_SIGMA_PX = 2.0
REFERENCE_SPACING = 2.8
SGMC_TOLERANCE = 0.98  # knowledge/27 §5.3: admissible rows may not lose >2 % relative on the second proxy
BOUNDARY_SPACING = max(THIN_SPACINGS)
INPUTS = ("inputs/h19_5_nan.tif", "inputs/dotted_h19_5_d2_8_nan.tif", "inputs/dotted_h19_5_d1_5_nan.tif",
          "sample_submission.tif", "labels.tif", "external/derived_sgmc_faults_100m_u8.tif")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(rel: str, root: Path) -> Path:
    """Accept either restore layout: ``<root>/<rel>`` (H31 group) or ``<root>/bridge/<rel>`` (core)."""
    for cand in (root / rel, root / "bridge" / rel):
        if cand.is_file():
            return cand
    raise SystemExit(f"missing restored input {rel} under {root} (run scripts/download_competition_data.sh)")


def git_state() -> dict:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - environment guard
        raise SystemExit(f"git state unavailable ({exc}); the sweep requires a clean committed tree") from exc
    return dict(revision=revision, branch=branch, dirty_worktree=dirty)


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "not-installed"


def build_rows(parent: np.ndarray, aware_score: np.ndarray) -> list[dict]:
    """Every frozen candidate/calibration row, as (id, family, spacing, mask). Construction only."""
    rows = [dict(id="cal_solid", family="calibration", spacing=1.0, mask=parent.copy())]
    for d in THIN_SPACINGS:
        rows.append(dict(id=f"thin_{d:g}", family="thin", spacing=d, mask=dot_thin(parent, d)))
    for d in AWARE_SPACINGS:
        rows.append(dict(id=f"aware_{d:g}", family="aware", spacing=d,
                         mask=score_ordered_dots(aware_score, parent, d)))
    rows.append(dict(id="cal_d1_5", family="calibration", spacing=1.5, mask=None))  # filled from the pin
    rows.append(dict(id="cal_d2_8", family="calibration", spacing=REFERENCE_SPACING, mask=None))
    return rows


def decide(summary_rows: dict, reference: dict) -> dict:
    """The frozen rule of knowledge/27 §5, applied to already-computed numbers only."""
    cat = {k: v["catalogue_hidden_mean"] for k, v in summary_rows.items()}
    sgmc = {k: v["sgmc_off_catalogue"]["dti"] for k, v in summary_rows.items()}
    calibrated = cat["cal_solid"] <= cat["cal_d1_5"] <= cat["cal_d2_8"]
    admissible = [k for k, v in summary_rows.items()
                  if v["family"] != "calibration"
                  and v["paired_vs_reference"]["mean"] > 0.0
                  and sgmc[k] >= SGMC_TOLERANCE * sgmc["cal_d2_8"]]
    if admissible:
        winner = max(admissible, key=lambda k: cat[k])
    else:
        winner = "cal_d2_8"
    return dict(
        proxy_calibration_check=dict(
            rule="catalogue_hidden(solid) <= (d1.5) <= (d2.8), i.e. the proxy reproduces the reported live ladder order",
            values=dict(solid=cat["cal_solid"], d1_5=cat["cal_d1_5"], d2_8=cat["cal_d2_8"]),
            calibrated=bool(calibrated),
        ),
        sgmc_tolerance=SGMC_TOLERANCE,
        admissible=[k for k in admissible],
        recommendation="cal_d2_8 (keep the pinned artifact)" if winner == "cal_d2_8" else winner,
        recommendation_is_boundary=bool(winner != "cal_d2_8" and summary_rows[winner]["spacing"] == BOUNDARY_SPACING),
        selection_labelled_measurement_only=not bool(calibrated),
        slot_implication="none: the slot rule requires beating holdout_best=0.14479018210246675 on the H34 "
                         "cell protocol; a file-level proxy comparison cannot clear it (knowledge/27 §5.5)",
        reference_catalogue_hidden=reference["catalogue_hidden_mean"],
        reference_sgmc=reference["sgmc_off_catalogue"]["dti"],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(EVIDENCE))
    ap.add_argument("--allow-dirty", action="store_true",
                    help="development only; the frozen run must be executed on a clean tree")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    if not PREREG.is_file():
        raise SystemExit(f"missing frozen preregistration: {PREREG}")
    out_dir.mkdir(parents=True, exist_ok=True)
    design_path, summary_path, rows_path = (out_dir / "design.json", out_dir / "summary.json",
                                            out_dir / "rows.jsonl")
    for p in (design_path, summary_path, rows_path):
        if p.exists():
            raise SystemExit(f"refusing to overwrite existing evidence {p}")
    state = git_state()
    if state["dirty_worktree"] and not args.allow_dirty:
        raise SystemExit("refusing to run from a dirty worktree; commit the implementation first")

    data = data_dir()
    paths = {rel: resolve(rel, data) for rel in INPUTS}
    parent = read_binary(paths["inputs/h19_5_nan.tif"])
    pinned_ref = read_binary(paths["inputs/dotted_h19_5_d2_8_nan.tif"])
    pinned_15 = read_binary(paths["inputs/dotted_h19_5_d1_5_nan.tif"])

    rows = build_rows(parent, gaussian_filter(parent.astype(np.float32), AWARE_SIGMA_PX))
    by_id = {r["id"]: r for r in rows}
    by_id["cal_d1_5"]["mask"] = pinned_15
    by_id["cal_d2_8"]["mask"] = pinned_ref
    if not np.array_equal(by_id[f"thin_{REFERENCE_SPACING:g}"]["mask"], pinned_ref):
        raise SystemExit("determinism control failed: dot_thin(parent, 2.8) does not reproduce the pinned "
                         "reference file; the run is void (knowledge/27 §3.1)")

    ctx = load_proxy_context(data)
    if parent.shape != ctx.foot.shape:
        raise SystemExit(f"parent shape {parent.shape} does not match the template {ctx.foot.shape}")

    summary_rows: dict[str, dict] = {}
    with rows_path.open("w") as sink:
        for r in rows:
            scored = score_mask(r["mask"], ctx, r["id"])
            paired = paired_catalogue_hidden(r["mask"], pinned_ref, ctx)
            row = dict(id=r["id"], family=r["family"], spacing=r["spacing"], **scored,
                       paired_vs_reference=paired, neighbour_profile=neighbour_profile(r["mask"]))
            summary_rows[r["id"]] = row
            sink.write(json.dumps(row) + "\n")
            sink.flush()
            print(f"{r['id']:>9}  emitted={row['emitted_pixels']:>7,}  "
                  f"cat_hidden={row['catalogue_hidden_mean']:.5f}  "
                  f"delta={paired['mean']:+.5f}  sgmc={row['sgmc_off_catalogue']['dti']:.5f}", flush=True)

    decision = decide(summary_rows, summary_rows["cal_d2_8"])
    design = dict(
        experiment="emission-density sweep on the frozen H19-5 habitat",
        preregistration=dict(path=str(PREREG.relative_to(ROOT)), sha256=sha256_file(PREREG)),
        frozen=dict(thin_spacings=list(THIN_SPACINGS), aware_spacings=list(AWARE_SPACINGS),
                    aware_sigma_px=AWARE_SIGMA_PX, reference_spacing=REFERENCE_SPACING,
                    sgmc_tolerance=SGMC_TOLERANCE, boundary_spacing=BOUNDARY_SPACING),
        protocol=dict(folds=[0, 1, 2, 3], draws=[20, 21],
                      source="src/gemsdoe/proxies.py (same code path as scripts/score_candidates.py)"),
        inputs={rel: dict(path=str(p.relative_to(ROOT)), sha256=sha256_file(p), bytes=p.stat().st_size)
                for rel, p in paths.items()},
        modules={f"gemsdoe/{m}": sha256_file(ROOT / "src" / "gemsdoe" / m)
                 for m in ("proxies.py", "thinning.py", "metric.py", "holdout.py")},
        git=state,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         packages={n: package_version(n) for n in ("scipy", "rasterio")}),
        seed_spend="none: fixed-file screen on the registered proxy draws 20/21 (no model fitted)",
    )
    design_path.write_text(json.dumps(design, indent=2) + "\n")
    summary = dict(experiment=design["experiment"], rows=summary_rows, decision=decision,
                   note="Proxy screens only. Both targets are catalogue-derived, neither is the organizer's "
                        "hidden expert label set, and no number here is a competition score.")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
