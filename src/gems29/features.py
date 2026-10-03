"""Dense feature assembly on the competition grid.

Raw inputs (all hash-pinned owner mirrors, see data/manifest.json):
  * the 19-band official feature stack (data/bridge/training_features.tif); band names/descriptions
    come from the file itself (verified 2026-10-03); band 6 `tc` is the known mislabel
    (IR-25-TC-BAND: values equal the radiometric total-count channel, not a magnetic derivative)
    and is kept as its own channel without magnetic-edge claims;
  * 12-band LiDAR scarp descriptor stack (USGS 3DEP 1 m derived, u8 quantised);
  * worm persistence rasters from worming.run_field;
  * distance-to-known-catalogue EDTs (computed per fold from KNOWN pixels only — never hidden truth).
"""

from __future__ import annotations

import numpy as np

RAW_BANDS = {
    1: "mag_anom", 2: "rtp", 3: "tmi_hg", 4: "geod_2ndinv", 5: "iso_grav_anom_slope", 6: "tc_radiometric",
    7: "geod_shearrate", 8: "geod_dilatationrate", 9: "tmi_vg", 10: "deq_n100a15",
    11: "iso_grav_anom_vg", 12: "det_elev", 13: "iso_grav_anom", 14: "tmi",
    15: "depth_to_base_surf", 16: "ieq_n100a15", 17: "cond_surf", 18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100"]  # strike (circular) & valid excluded


def robust_scale(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(a - p5)/(p95 - p5) clipped to [0,1]; 0 where invalid."""
    v = a[valid]
    lo, hi = np.quantile(v, (0.05, 0.95))
    out = np.clip((a - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return np.where(valid, out, 0.0).astype(np.float32)


def dequant_lidar(q: np.ndarray, how: str, xmax_or_gain: float) -> np.ndarray:
    """Invert q = 1 + round(254 * t(x/xmax)) from the sibling quantisation table (linear or sqrt)."""
    from .gridio import dequantize
    return dequantize(q, xmax_or_gain, how)


def build_feature_dict(*, raw_path, lidar_path, worm_dir, known_catalog: np.ndarray,
                       valid: np.ndarray) -> tuple[dict[str, np.ndarray], list[str]]:
    """Return ({name: float32 2-D array in [0,1]-ish scale}, ordered names). All finite; 0 outside."""
    import rasterio
    feats: dict[str, np.ndarray] = {}
    with rasterio.open(raw_path) as ds:
        for b, name in RAW_BANDS.items():
            a = ds.read(b).astype(np.float32)
            v = valid & np.isfinite(a) & (a > -1e37)
            feats[f"raw_{name}"] = robust_scale(np.where(v, a, 0.0), v)
    with rasterio.open(lidar_path) as ds:
        for i, name in enumerate(LIDAR_BANDS, start=1):
            q = ds.read(i)
            feats[f"lid_{name}"] = (np.where(valid & (q > 0), (q.astype(np.float32) - 1.0) / 254.0, 0.0))
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(~known_catalog) - 1.0  # 0 on catalogue pixels
    d = np.clip(d, 0, 30)
    feats["dist_known_px_norm"] = (d / 30.0).astype(np.float32)
    feats["dist_known_collapse"] = np.exp(-d / 4.0).astype(np.float32)
    for key, fname in [("worm_mag_persist", "worm_mag_persist.tif"),
                       ("worm_grav_persist", "worm_grav_persist.tif"),
                       ("worm_joint_persist", "worm_joint_persist.tif"),
                       ("worm_joint_defined", "worm_joint_defined.tif")]:
        import rasterio as rio
        p = worm_dir / fname
        if p.exists():
            with rio.open(p) as ds:
                a = ds.read(1).astype(np.float32)
            feats[key] = np.where(valid & np.isfinite(a), np.nan_to_num(a), 0.0)
    names = list(feats)
    return feats, names


def sample_rows(feats: dict[str, np.ndarray], names: list[str], sel_y: np.ndarray, sel_x: np.ndarray,
                label_arr: np.ndarray, sample_weight: np.ndarray | None = None):
    X = np.stack([feats[n][sel_y, sel_x] for n in names], axis=1).astype(np.float32)
    y = label_arr[sel_y, sel_x].astype(np.int8)
    return X, y, sample_weight


def dense_rows(feats: dict[str, np.ndarray], names: list[str], chunk: int = 500_000):
    """Yield (slice_index, X_chunk) row-chunks in raster order for dense prediction."""
    any_arr = next(iter(feats.values()))
    n = int(np.prod(any_arr.shape))
    starts = range(0, n, chunk)
    H = any_arr.shape[0]
    W = any_arr.shape[1]
    for s in starts:
        e = min(s + chunk, n)
        X = np.stack([feats[nm].reshape(-1)[s:e] for nm in names], axis=1).astype(np.float32)
        yield slice(s, e), X
