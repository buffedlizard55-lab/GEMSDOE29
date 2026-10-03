"""Raster I/O helpers: read the pinned grids, write float32 GeoTIFFs on the competition grid."""

from __future__ import annotations

import numpy as np
import rasterio

from . import paths


def read_band(tif_path, band: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Read one band; return (float32 values with nodata->nan, valid finite mask)."""
    with rasterio.open(tif_path) as ds:
        a = ds.read(band).astype(np.float32)
    valid = np.isfinite(a) & (a > -1e37)
    out = np.where(valid, a, np.nan).astype(np.float32)
    return out, valid


def write_raster(arr: np.ndarray, out_path, *, valid: np.ndarray | None = None,
                 dtype: str = "float32") -> None:
    with rasterio.open(paths.DATA / "bridge" / "sample_submission.tif") as tpl:
        prof = tpl.profile.copy()
    prof.update(dtype=dtype, count=1, nodata=None)
    if np.issubdtype(np.asarray(arr).dtype, np.floating) and dtype == "float32":
        prof.update(nodata=np.nan)
    out = np.asarray(arr)
    if valid is not None:
        out = np.where(valid, out, np.nan if dtype == "float32" else 0).astype(dtype)
    else:
        out = out.astype(dtype)
    with rasterio.open(out_path, "w", **prof) as ds:
        ds.write(out, 1)


def dequantize(q: np.ndarray, xmax: float, how: str = "linear") -> np.ndarray:
    """Invert q = 1 + round(254 * t(x/xmax)); q == 0 -> NaN. t = linear or sqrt transform."""
    q = np.asarray(q, np.float32)
    t = (q - 1.0) / 254.0
    if how == "sqrt":
        x = (t * t) * xmax
    else:
        x = t * xmax
    return np.where(q > 0, x, np.nan).astype(np.float32)
