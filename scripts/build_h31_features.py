#!/usr/bin/env python3
"""Build the frozen H31 scale-persistence cache from the prepared 100-m magnetic/gravity bands."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.paths import work_dir  # noqa: E402
from gemsdoe.worms import H31_NAMES, WormConfig, build_h31_features  # noqa: E402


PREREG = ROOT / "knowledge" / "02_preregistered_h31_worming_2026-10-03.md"
OUTPUT_NAME = "h31_potential_persistence.npy"


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="output .npy path; refuses to overwrite it")
    args = parser.parse_args()

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
    if out.exists() or out.with_suffix(out.suffix + ".partial").exists() or any(path.exists() for path in sidecars):
        raise SystemExit(f"refusing to overwrite existing H31 output, sidecar, or partial file: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    footprint = np.load(required["footprint"], mmap_mode="r")
    fi = np.flatnonzero(np.asarray(footprint, dtype=bool).ravel())
    rtp = np.load(required["rtp"], mmap_mode="r")
    gravity = np.load(required["iso_grav_anom"], mmap_mode="r")
    if rtp.shape != footprint.shape or gravity.shape != footprint.shape:
        raise SystemExit("prepared rtp/gravity arrays do not align with the sample footprint")

    features, diagnostics = build_h31_features(
        rtp,
        gravity,
        footprint,
        fi,
        config=WormConfig(),
    )
    if features.shape != (len(H31_NAMES), fi.size):
        raise SystemExit(f"unexpected H31 feature shape {features.shape}")

    partial = out.with_suffix(out.suffix + ".partial")
    mm = np.lib.format.open_memmap(partial, mode="w+", dtype=np.float32, shape=features.shape)
    mm[:] = features
    mm.flush()
    del mm
    partial.replace(out)

    names_path = Path(str(out) + ".names.json")
    meta_path = Path(str(out) + ".metadata.json")
    names_path.write_text(json.dumps(H31_NAMES, indent=2) + "\n")
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = "unknown", True
    metadata = {
        "schema_version": 1,
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "code_revision": revision,
        "dirty_worktree_at_cache_build": dirty,
        "input_arrays": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for name, path in required.items()
        },
        "output": {
            "path": str(out),
            "bytes": out.stat().st_size,
            "sha256": sha256_file(out),
            "shape": list(features.shape),
            "dtype": str(features.dtype),
            "feature_names": H31_NAMES,
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": package_version("numpy"),
            "scipy": package_version("scipy"),
        },
        "diagnostics": diagnostics,
        "provenance_warning": (
            "Prepared arrays originate from hash-pinned owner mirrors. A hash pin proves byte integrity against the "
            "recorded owner revision, not organizer authentication. This H31 feature is a worming-like proxy, not a "
            "full Poisson-wavelet inversion."
        ),
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes; sha256={metadata['output']['sha256']})")
    print(f"Wrote {names_path} and {meta_path}")
    print(f"PSG seeds={diagnostics['psg']['zero_height_seed_count']:,}; gravity seeds={diagnostics['isostatic_gravity']['zero_height_seed_count']:,}; joint nonzero={diagnostics['joint_persistence_nonzero_fraction']:.6f}")


if __name__ == "__main__":
    main()
