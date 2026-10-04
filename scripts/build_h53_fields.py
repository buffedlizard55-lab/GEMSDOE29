#!/usr/bin/env python3
"""Build and cache the H53 cross-scale topographic fabric fields (label-free; no fit, no holdout read).

Writes ``data/work/h53_fields.npy`` (``(len(H53_NAMES), n_footprint)`` float32, footprint-vector
order) and ``data/work/h53_fields.json`` (frozen parameters, input hashes and diagnostics). Nothing
here reads ``labels.tif``, the catalogue or any fitted quantity: the fields are a pure function of the
cached 100 m elevation band and the footprint.

    python scripts/build_h53_fields.py [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.h53 import H53_NAMES, H53Config, build_h53_fields  # noqa: E402
from gemsdoe.paths import work_dir  # noqa: E402

FIELDS = "h53_fields.npy"
META = "h53_fields.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild even if a cache exists")
    args = parser.parse_args()

    work = work_dir()
    out_fields, out_meta = work / FIELDS, work / META
    if out_fields.is_file() and out_meta.is_file() and not args.force:
        print(f"cached: {out_fields.relative_to(ROOT)} (use --force to rebuild)")
        return 0

    foot = np.load(work / "bands" / "_footprint.npy")
    fi = np.flatnonzero(foot.ravel())
    config = H53Config()
    t0 = time.time()
    vectors, _grids, diag = build_h53_fields(work / "bands", foot, fi, config=config)
    elapsed = time.time() - t0

    np.save(out_fields, vectors)
    band = work / "bands" / config.elev_band
    meta = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        elapsed_s=round(elapsed, 1),
        names=list(H53_NAMES),
        config=dict(scales_px=[float(s) for s in config.scales_px],
                    tensor_sigma_factor=float(config.tensor_sigma_factor),
                    tol_deg=float(config.tol_deg), coherence_min=float(config.coherence_min),
                    min_contrast_fraction=float(config.min_contrast_fraction),
                    elev_band=config.elev_band),
        inputs={config.elev_band: sha256_file(band)},
        diagnostics=diag,
        label_free=True,
    )
    out_meta.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")

    print(f"built {len(H53_NAMES)} H53 fields over {fi.size:,} footprint px in {elapsed:.1f}s")
    for i, name in enumerate(H53_NAMES):
        row = vectors[i]
        print(f"  {name:14s} nonzero {np.mean(row > 0):.4f}  mean {row.mean():.4f}  max {row.max():.4f}")
    print(f"wrote {out_fields.relative_to(ROOT)}, {out_meta.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
