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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.proxies import (  # noqa: E402
    load_proxy_context,
    paired_catalogue_hidden,
    read_binary,
    score_mask,
)
from gemsdoe.submission import check_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", action="append", required=True, help="candidate TIF (repeatable)")
    ap.add_argument("--reference", default=None, help="reference TIF scored with the same targets for paired deltas")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "candidate_scoreboard.json"))
    args = ap.parse_args()

    data = data_dir()
    ctx = load_proxy_context(data)
    foot = ctx.foot

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
        mask = read_binary(path)
        if mask.shape != foot.shape:
            raise SystemExit(f"{path} shape {mask.shape} does not match the template {foot.shape}")
        masks[str(path)] = mask
        row = score_mask(mask, ctx, path.name)
        row["format_check"] = check_file(path, data / "sample_submission.tif")
        report["files"][str(path)] = row
        print(f"{path.name}: catalogue_hidden={row['catalogue_hidden_mean']:.5f} "
              f"sgmc={row['sgmc_off_catalogue']['dti']:.5f} emitted={row['emitted_pixels']:,} "
              f"hug={row['hug_share']:.3f} format_ok={row['format_check'].get('ok_to_upload')}")

    if args.reference:
        ref = masks[str(Path(args.reference))]
        for path_str in args.candidate:
            paired = paired_catalogue_hidden(masks[str(Path(path_str))], ref, ctx)
            report["deltas"][str(path_str)] = dict(
                vs=args.reference,
                catalogue_hidden=paired["cells"],
                catalogue_hidden_mean=paired["mean"],
            )
            print(f"delta vs reference ({Path(args.reference).name}): "
                  f"mean {report['deltas'][str(path_str)]['catalogue_hidden_mean']:+.5f}")
    Path(args.out).write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
