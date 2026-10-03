#!/usr/bin/env python3
"""Build the H34 candidate GeoTIFF: the group's best habitat, re-emitted by coverage optimisation.

Habitat is deliberately **unchanged**: the H19-5 lineament set (the parent of the file with the
owner-reported 0.2477/0.2600 scores) taken from the hash-pinned owner mirror
(``data/inputs/h19_5_nan.tif``, sha256 ``ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d``).
Only the *placement* of the dots changes, at an identical dot count (44,090 = the historical D2.8 file),
so the comparison is habitat-neutral and budget-neutral.

The emission is the residual-greedy covering of ``src/gemsdoe/coverage.py``; the script reports the
truth-free objective (kernel-captured parent mass) of the new file against the historical D2.8 geometry,
plus the marginal credit per dot at the chosen budget so the metric's own tau rule can be checked.

Nothing here contacts DrivenData; no labels or scores are read for the emission. Outputs go to
``--out-dir`` (default ``docs/downloads``) with a sibling ``checks-*.json`` receipt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.coverage import greedy_coverage, kernel_cover  # noqa: E402
from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.submission import check_file, content_id, make_filename, make_note, sha256_file, write_submission, zip_single  # noqa: E402

H19_5_SHA = "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"
D28_PX = 44_090
DATE = "20261003"


def load_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1)
    if a.dtype == np.int8:
        return a == 1
    return np.isfinite(a) & (a > 0)


def captured_mass(prior: np.ndarray, emission: np.ndarray, radius: float = 3.0) -> float:
    return float((prior.astype(np.float32) * kernel_cover(emission, radius)).sum())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "docs" / "downloads"))
    ap.add_argument("--equal-budget", type=int, default=D28_PX)
    ap.add_argument("--min-sep", type=float, default=2.0)
    ap.add_argument("--extend", type=float, default=0.0, help="extra dots beyond the equal budget (fraction)")
    args = ap.parse_args()

    data = data_dir()
    parent = data / "h19_5_nan.tif"  # hash-pinned H19-5 owner mirror restored by restore_data.py
    d28 = ROOT / "docs" / "downloads" / "gemsdoe29-historical-d28-20261002-e56ea318af89-nan.tif"
    if not parent.is_file():
        raise SystemExit(
            f"missing the hash-pinned H19-5 mirror at {parent}; restore it (GEMSDOE24@07345ea0, "
            "inputs/gems19-h19-5-...-e27054cf-nan.tif) or point GEMS_DATA_DIR at a restored directory"
        )
    digest = sha256_file(parent)
    if digest != H19_5_SHA:
        raise SystemExit(f"H19-5 mirror hash mismatch: {digest} != {H19_5_SHA}")
    if not d28.is_file():
        raise SystemExit(f"missing the historical D2.8 file for the equal-budget comparison at {d28}")

    prior = load_mask(parent)
    template = data / "sample_submission.tif"
    labels = load_mask(data / "labels.tif")
    hist = load_mask(d28)
    with rasterio.open(template) as t:
        footprint = np.isfinite(t.read(1))

    budgets = [args.equal_budget]
    if args.extend > 0:
        budgets.append(int(round(args.equal_budget * (1 + args.extend))))
    result = greedy_coverage(
        prior.astype(np.float32), footprint, budgets=tuple(budgets), radius_px=3.0, min_sep_px=args.min_sep, gain_floor=0.05
    )
    chosen_budget = budgets[-1]
    emission = result.emissions[chosen_budget]

    hist_mass = captured_mass(prior, hist)
    new_mass = captured_mass(prior, emission)
    levels = result.levels
    tail = levels[-1] if levels else {}
    diag = dict(
        parent="H19-5 owner mirror",
        parent_sha256=digest,
        parent_pixels=int(prior.sum()),
        historical_d28=dict(
            path=str(d28.relative_to(ROOT)),
            pixels=int(hist.sum()),
            captured_parent_mass=hist_mass,
            share_of_parent=hist_mass / float(prior.sum()),
            credit_per_dot=hist_mass / max(int(hist.sum()), 1),
        ),
        candidate=dict(
            pixels=int(emission.sum()),
            captured_parent_mass=new_mass,
            share_of_parent=new_mass / float(prior.sum()),
            credit_per_dot=new_mass / max(int(emission.sum()), 1),
        ),
        relative_captured_gain=(new_mass / hist_mass - 1.0) if hist_mass else None,
        equal_budget=bool(int(emission.sum()) == int(hist.sum())),
        min_sep_px=args.min_sep,
        radius_px=3.0,
        greedy_levels=levels,
        greedy_diagnostics=result.diagnostics,
        tau_rule=dict(
            note="tau = 0.2*TP/(0.2*FP + 0.8*|G|); a dot is worth emitting while its credit/FP mass exceeds tau",
            tau_conditional_model=0.045,
            conditional_scale_note="sibling H28 model implies truth credit ~ 0.054 x captured parent mass (anchors unverified)",
            greedy_tp_hat_units="kernel-captured parent mass units, not truth credit",
            greedy_tp_hat_tail=float(tail.get("tp_hat", float("nan"))),
        ),
    )
    print(json.dumps({k: v for k, v in diag.items() if k not in ("greedy_levels", "greedy_diagnostics")}, indent=2))
    print("greedy levels:", json.dumps([{kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in row.items()} for row in levels]))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cid = content_id(emission.astype(np.float32), footprint, labels)
    slug = f"h34-cover{int(round(emission.sum() / 1000.0))}k-m{str(args.min_sep).replace('.', 'p')}"
    tif = out_dir / make_filename(slug, DATE, cid, "nan")
    write_submission(emission.astype(np.float32), template, tif, outside="nan")
    checks = check_file(tif, template)
    digest_out = sha256_file(tif)
    receipt = dict(
        file=tif.name,
        content_id=cid,
        sha256=digest_out,
        bytes=tif.stat().st_size,
        emitted_pixels=int(emission.sum()),
        diagnostics=diag,
        format_check=checks,
        status=(
            "format-validated against the owner-mirror template; habitat unchanged from the historical parent; "
            "emission geometry validated only on proxies; unscored; not slot-approved"
        ),
        note=make_note("H34", "coverage emission on H19-5 habitat; unscored; not slot-approved", cid),
    )
    (out_dir / f"checks-{tif.stem}.json").write_text(json.dumps(receipt, indent=2, default=float) + "\n")
    zpath = zip_single(tif)
    print(f"wrote {tif} ({tif.stat().st_size:,} B, sha256 {digest_out[:16]}..., content id {cid})")
    print(f"wrote checks-{tif.stem}.json and {zpath.name}")
    if not checks.get("ok_to_upload", False):
        print("FORMAT CHECK FAILED:", json.dumps(checks.get("hard_failures", checks), indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
