"""Turn the restored rasters into fast per-band ``.npy`` arrays, the footprint and the label mask."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .features import BASE_NAMES


def prepare_inputs(data_dir: Path, work_dir: Path) -> dict:
    bands = work_dir / "bands"
    bands.mkdir(parents=True, exist_ok=True)
    with rasterio.open(data_dir / "sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(data_dir / "labels.tif") as s:
        lab = s.read(1) == 1
    np.save(bands / "_footprint.npy", foot)
    np.save(bands / "_labels.npy", lab)
    with rasterio.open(data_dir / "training_features.tif") as s:
        names = [s.tags(i)["band_name"] for i in range(1, s.count + 1)]
        if names != BASE_NAMES:
            raise SystemExit(f"unexpected band order: {names}")
        nd = s.nodata
        for i, n in enumerate(names, 1):
            a = s.read(i).astype(np.float32)
            a[(a == nd) | ~np.isfinite(a) | (a < -1e38)] = np.nan
            np.save(bands / f"{i:02d}_{n}.npy", a)
    return dict(footprint_px=int(foot.sum()), label_px=int(lab.sum()), bands=len(BASE_NAMES))
