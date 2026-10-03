#!/usr/bin/env python3
"""Build the H40 dense continuation-persistence cache (footprint-vector memmap + diagnostics).

Reads only the prepared magnetic/gravity bands (02_rtp.npy, 13_iso_grav_anom.npy) and the footprint.
No labels or catalogue geometry enter this cache; the fields are pure physics and are therefore static
across folds/draws (unlike the per-draw H35 interaction fields, which are computed by the screen runner
from each draw's *visible* catalogue).

Usage (frozen constants; refusal to overwrite):

    GEMS_DATA_DIR=... GEMS_WORK_DIR=... python3 scripts/build_h40_features.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.dense_persist import HP_NAMES, build_dense_persistence  # noqa: E402
from gemsdoe.paths import work_dir  # noqa: E402
from gemsdoe.worms import WormConfig  # noqa: E402

PREREG = ROOT / "knowledge" / "19_preregistered_h35_h40_screen_2026-10-03.md"
OUTPUT_NAME = "h40_dense_persistence.npy"
HEIGHTS_M = (0, 100, 200, 400, 800, 1_200)  # the frozen H31 ladder (worms.H31_HEIGHTS_M)
TOL_PX = 2.0
SMOOTH_PX = 1.0
EDGE_PCTL = 90.0
GUARD_PX = 16


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None, help="output .npy path; refuses to overwrite it")
    args = ap.parse_args()
    if not PREREG.is_file():
        raise SystemExit(f"missing preregistration document: {PREREG} (frozen gates required before feature caching)")
    work = work_dir()
    band_dir = work / "bands"
    required = {
        "rtp": band_dir / "02_rtp.npy",
        "iso_grav_anom": band_dir / "13_iso_grav_anom.npy",
        "footprint": band_dir / "_footprint.npy",
    }
    for name, path in required.items():
        if not path.is_file():
            raise SystemExit(f"missing prepared input {name}: {path}; run scripts/prepare_data.py first")
    out = Path(args.out) if args.out else work / OUTPUT_NAME
    sidecars = [Path(str(out) + ".names.json"), Path(str(out) + ".metadata.json")]
    if out.exists() or out.with_suffix(out.suffix + ".partial").exists() or any(p.exists() for p in sidecars):
        raise SystemExit(f"refusing to overwrite existing H40 output, sidecar, or partial file: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    footprint = np.load(required["footprint"], mmap_mode="r")
    fi = np.flatnonzero(np.asarray(footprint, dtype=bool).ravel())
    cfg = WormConfig(heights_m=HEIGHTS_M, edge_percentile=EDGE_PCTL, boundary_guard_px=GUARD_PX)
    t0 = time.time()
    fields, diag = build_dense_persistence(band_dir, footprint, fi, config=cfg, tol_px=TOL_PX, smooth_sigma_px=SMOOTH_PX)
    if fields.shape != (len(HP_NAMES), fi.size):
        raise SystemExit(f"unexpected H40 feature shape {fields.shape}")
    if not np.isfinite(fields).all() or fields.min() < 0 or fields.max() > 1:
        raise SystemExit("H40 features violated [0,1]/finite invariants")

    partial = out.with_suffix(out.suffix + ".partial")
    mm = np.lib.format.open_memmap(partial, mode="w+", dtype=np.float32, shape=fields.shape)
    mm[:] = fields
    mm.flush()
    del mm
    partial.replace(out)

    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_revision": revision,
        "elapsed_s": round(time.time() - t0, 1),
        "config": {"heights_m": list(HEIGHTS_M), "tol_px": TOL_PX, "smooth_px": SMOOTH_PX,
                   "edge_percentile": EDGE_PCTL, "boundary_guard_px": GUARD_PX},
        "inputs": {k: sha256_file(p) for k, p in required.items()},
        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha256_file(PREREG)},
        "module": {"gemsdoe.dense_persist": sha256_file(ROOT / "src/gemsdoe/dense_persist.py"),
                   "gemsdoe.worms": sha256_file(ROOT / "src/gemsdoe/worms.py")},
        "packages": {"python": sys.version.split()[0], "numpy": np.__version__,
                     **{n: package_version(n) for n in ("scipy", "scikit-learn", "rasterio")}},
        "diagnostics": diag,
        "output_sha256": sha256_file(out),
        "note": "Owner-mirror-derived physics cache. Not organizer-authenticated. No labels used.",
    }
    Path(str(out) + ".names.json").write_text(json.dumps(HP_NAMES, indent=2) + "\n")
    Path(str(out) + ".metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"out": str(out), "sha256": meta["output_sha256"], "elapsed_s": meta["elapsed_s"],
                      "nonzero_fraction": diag["nonzero_fraction"]}, indent=2))


if __name__ == "__main__":
    main()
