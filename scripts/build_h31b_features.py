#!/usr/bin/env python3
"""Build the H31b dense worming feature cache (family W, 12 columns).

Frozen design: knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md. Regenerable; the
cache and metadata live in the ignored work directory. Re-running rebuilds in place; the screen
runner refuses to use a cache whose builder source hash does not match the committed module, so
stale caches cannot silently enter a screen.

    python scripts/build_h31b_features.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.features import BASE_NAMES  # noqa: E402
from gemsdoe.paths import work_dir  # noqa: E402
from gemsdoe.wormdense import (  # noqa: E402
    W_NAMES,
    build_w_features,
    write_cache,
)

CACHE = "wormdense_features.npy"
META = "wormdense_features.json"
SPARSE_WARN = 0.05  # a W column below 5% nonzero would repeat the H31 sparsity defect


def main() -> int:
    t0 = time.time()
    w = work_dir()
    bands = w / "bands"
    foot = np.load(bands / "_footprint.npy")
    names = json.loads((bands / "_bands.names.json").read_text()) if (bands / "_bands.names.json").exists() else None

    def band(name: str) -> tuple[np.ndarray, Path]:
        idx = BASE_NAMES.index(name)
        p = bands / f"{idx + 1:02d}_{name}.npy"
        if not p.is_file():
            raise SystemExit(f"missing prepared band {p}")
        return np.load(p, mmap_mode="r"), p

    if names is not None:
        for name in ("rtp", "iso_grav_anom"):
            idx = BASE_NAMES.index(name)
            if idx < len(names) and names[idx] != name:
                raise SystemExit(f"band name mismatch at index {idx}: {names[idx]!r} != {name!r}")

    rtp, rtp_path = band("rtp")
    grav, grav_path = band("iso_grav_anom")
    print(f"bands: rtp={rtp_path.name} shape={np.asarray(rtp).shape} "
          f"finite_fraction={float(np.isfinite(np.asarray(rtp, np.float32)).mean()):.3f}; "
          f"grav={grav_path.name}", flush=True)

    features, metadata = build_w_features(bands, foot, np.asarray(rtp, np.float32),
                                          np.asarray(grav, np.float32))

    rev = "unknown"
    try:
        rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    input_hashes = {
        "bands/rtp": _sha256(rtp_path),
        "bands/iso_grav_anom": _sha256(grav_path),
        "bands/_footprint": _sha256(bands / "_footprint.npy"),
    }
    builder_sha = _sha256(ROOT / "src" / "gemsdoe" / "wormdense.py")
    meta = write_cache(w / CACHE, w / META, features, metadata, input_hashes, rev, builder_sha)

    print(f"H31b dense worming cache: {features.shape[0]} columns x {features.shape[1]} px "
          f"in {time.time() - t0:.0f}s; code revision {rev[:12]}", flush=True)
    sparse = []
    for i, n in enumerate(W_NAMES):
        st = meta["column_stats"][n]
        print(f"  {n:<14} nonzero={st['nonzero_fraction'] * 100:6.2f}%  "
              f"p50={st['p50']:.3f} p95={st['p95']:.3f} max={st['max']:.3f}", flush=True)
        if st["nonzero_fraction"] < SPARSE_WARN:
            sparse.append(n)
    if sparse:
        print(f"WARNING: sparse W columns (repeat of the H31 defect): {sparse}", file=sys.stderr)
    print(f"cache sha256: {meta['output_sha256']}")
    print(f"work directory: {w}")
    return 0


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
