#!/usr/bin/env python3
"""Score fixed candidate GeoTIFFs (no model fitting) on the two registered proxy targets.

This is the file-level screen used before a weekly slot: any candidate artifact can be compared with the
historical reference on the *same* target definitions and folds, without fitting anything, because the
emissions are fixed.

Targets
-------
1. ``catalogue_hidden``: the repository's hide-and-recover proxy. For each of the four quadrant folds and
   the two registered draws, the hidden catalogue components in the quadrant are the truth; the visible
   catalogue is masked out of the score (``known``). This is a *catalogue-gap* proxy, not new-fault truth.
2. ``sgmc_off_catalogue``: state-geologic-map faults that are neither catalogue pixels nor within 300 m of
   one (``external/derived_sgmc_faults_100m_u8.tif``). Independent of the supplied catalogue by
   construction; its live-score relationship is peer-reported, not established here.

    GEMS_DATA_DIR=/tmp/gemsdoe29-data python3 scripts/score_candidates.py \
        --candidate docs/downloads/<file>.tif --reference docs/downloads/<historical>.tif \
        --out evidence/candidate_scoreboard.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.holdout import Holdout  # noqa: E402
from gemsdoe.metric import dti_binary  # noqa: E402
from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.submission import check_file  # noqa: E402

FOLDS = (0, 1, 2, 3)
DRAWS = (20, 21)
DOMAIN_ERODE = 12


def read_bool(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def score(name: str, mask: np.ndarray, foot: np.ndarray, labels: np.ndarray, sgmc: np.ndarray,
          holdout: Holdout, near_vis: np.ndarray) -> dict:
    folds = {}
    for draw_seed in DRAWS:
        for fold in FOLDS:
            d = holdout.draw(fold, draw_seed)
            domain = binary_erosion(d.quadrant, iterations=DOMAIN_ERODE)
            truth = d.hidden_test & domain
            emit = mask & domain
            r = dti_binary(emit, truth, valid=domain, known=d.visible)
            folds[f"draw{draw_seed}_fold{fold}"] = dict(
                dti=float(r["dti"]), coverage=float(r["coverage"]), tp=float(r["tp"]), fp=float(r["fp"]),
                n_truth=int(r["n_truth"]), emitted=int(emit.sum()),
            )
    cat = np.array([v["dti"] for v in folds.values()])
    per_draw = {f"draw{ds}": float(np.mean([v["dti"] for k, v in folds.items() if k.startswith(f"draw{ds}")]))
                for ds in DRAWS}
    sg = dti_binary(mask, sgmc, valid=foot, known=labels)
    n = int(mask.sum())
    return dict(
        name=name,
        catalogue_hidden_mean=float(cat.mean()),
        catalogue_hidden_per_draw=per_draw,
        catalogue_hidden_folds=folds,
        catalogue_hidden_folds_positive_vs_zero=float((cat > 0).mean()),
        sgmc_off_catalogue=dict(dti=float(sg["dti"]), coverage=float(sg["coverage"]), tp=float(sg["tp"]),
                                fp=float(sg["fp"]), n_truth=int(sg["n_truth"])),
        emitted_pixels=n,
        hug_share=float((mask & near_vis).sum() / max(n, 1)),
        on_catalogue_pixels=int((mask & labels).sum()),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", action="append", required=True, help="candidate TIF (repeatable)")
    ap.add_argument("--reference", default=None, help="reference TIF scored with the same targets for paired deltas")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "candidate_scoreboard.json"))
    args = ap.parse_args()

    data = data_dir()
    with rasterio.open(data / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = read_bool(data / "labels.tif")
    with rasterio.open(data / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = ds.read(1) > 0
    sgmc_off = sgm & ~labels & ~binary_dilation(labels, iterations=3)
    holdout = Holdout(foot, labels, 0.20)
    near_vis = binary_dilation(labels, iterations=3)

    report: dict = dict(
        targets=dict(
            catalogue_hidden="masked DTI on hidden catalogue components, 4 folds x draws 20/21 (catalogue-gap proxy)",
            sgmc_off_catalogue="masked DTI against state-map faults >=300 m from the supplied catalogue",
        ),
        files={},
        reference=args.reference,
        deltas={},
        note="Proxy screens only. Neither target is the organizer's hidden expert label set and neither "
             "score is a competition score. Format checks are local.",
    )
    masks = {}
    for path_str in [*args.candidate, *([args.reference] if args.reference else [])]:
        path = Path(path_str)
        if not path.is_file():
            raise SystemExit(f"missing file {path}")
        mask = read_bool(path)
        if mask.shape != foot.shape:
            raise SystemExit(f"{path} shape {mask.shape} does not match the template {foot.shape}")
        masks[str(path)] = mask
        row = score(path.name, mask, foot, labels, sgmc_off, holdout, near_vis)
        row["format_check"] = check_file(path, data / "sample_submission.tif")
        report["files"][str(path)] = row
        print(f"{path.name}: catalogue_hidden={row['catalogue_hidden_mean']:.5f} "
              f"sgmc={row['sgmc_off_catalogue']['dti']:.5f} emitted={row['emitted_pixels']:,} "
              f"hug={row['hug_share']:.3f} format_ok={row['format_check'].get('ok_to_upload')}")

    if args.reference:
        ref = masks[str(Path(args.reference))]
        for path_str in args.candidate:
            m = masks[str(Path(path_str))]
            deltas = {}
            for draw_seed in DRAWS:
                for fold in FOLDS:
                    dd = holdout.draw(fold, draw_seed)
                    dom = binary_erosion(dd.quadrant, iterations=DOMAIN_ERODE)
                    a = dti_binary(m & dom, dd.hidden_test & dom, valid=dom, known=dd.visible)
                    b = dti_binary(ref & dom, dd.hidden_test & dom, valid=dom, known=dd.visible)
                    deltas[f"draw{draw_seed}_fold{fold}"] = float(a["dti"] - b["dti"])
            report["deltas"][str(path_str)] = dict(
                vs=args.reference,
                catalogue_hidden=deltas,
                catalogue_hidden_mean=float(np.mean(list(deltas.values()))),
            )
            print(f"delta vs reference ({Path(args.reference).name}): "
                  f"mean {report['deltas'][str(path_str)]['catalogue_hidden_mean']:+.5f}")
    Path(args.out).write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
