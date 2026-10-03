"""Dense feature assembly on the competition grid.

Raw inputs are hash-pinned owner mirrors (see data/manifest.json): the 19-band feature stack,
12-band LiDAR derivatives, corrected worming rasters, and per-fold catalogue-distance transforms.
The mirrors are not organizer-authenticated. Band 6 is the known radiometric total-count channel,
not a magnetic derivative; it is retained without magnetic-edge claims.
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
               "upface_max", "cross_max", "relief", "coh100"]


def robust_scale(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(a - p5)/(p95 - p5) clipped to [0,1]; 0 where invalid."""
    a = np.asarray(a)
    valid = np.asarray(valid, bool) & np.isfinite(a)
    if not valid.any():
        return np.zeros(a.shape, np.float32)
    lo, hi = np.quantile(a[valid], (0.05, 0.95))
    out = np.clip((a - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return np.where(valid, out, 0.0).astype(np.float32)


def dequant_lidar(q: np.ndarray, how: str, xmax_or_gain: float) -> np.ndarray:
    """Invert q = 1 + round(254 * t(x/xmax)) from the sibling quantisation table."""
    from .gridio import dequantize
    return dequantize(q, xmax_or_gain, how)


def build_feature_dict(*, raw_path, lidar_path, worm_dir, known_catalog: np.ndarray,
                       valid: np.ndarray) -> tuple[dict[str, np.ndarray], list[str]]:
    """Return float32 feature rasters; invalid/out-of-footprint cells are finite zero."""
    import rasterio
    valid = np.asarray(valid, bool)
    feats: dict[str, np.ndarray] = {}
    with rasterio.open(raw_path) as ds:
        for b, name in RAW_BANDS.items():
            a = ds.read(b).astype(np.float32)
            v = valid & np.isfinite(a) & (a > -1e37)
            feats[f"raw_{name}"] = robust_scale(np.where(v, a, 0.0), v)
    with rasterio.open(lidar_path) as ds:
        for i, name in enumerate(LIDAR_BANDS, start=1):
            q = ds.read(i)
            feats[f"lid_{name}"] = np.where(valid & (q > 0), (q.astype(np.float32) - 1.0) / 254.0, 0.0)
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(~np.asarray(known_catalog, bool)) - 1.0
    d = np.clip(d, 0, 30)
    feats["dist_known_px_norm"] = (d / 30.0).astype(np.float32)
    feats["dist_known_collapse"] = np.exp(-d / 4.0).astype(np.float32)

    worm_files = {
        "worm_mag_persist": ("worm_mag_persist.tif", 1.0),
        "worm_grav_persist": ("worm_grav_persist.tif", 1.0),
        "worm_joint_persist": ("worm_joint_persist.tif", 1.0),
        "worm_joint_defined": ("worm_joint_defined.tif", 1.0),
        "worm_mag_strength_ratio": ("worm_mag_strength_ratio.tif", 2.0),
        "worm_grav_strength_ratio": ("worm_grav_strength_ratio.tif", 2.0),
        "worm_joint_strength_ratio": ("worm_joint_strength_ratio.tif", 2.0),
    }
    for key, (fname, upper) in worm_files.items():
        p = worm_dir / fname
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1).astype(np.float32)
        finite = valid & np.isfinite(a)
        if finite.any() and (np.any(a[finite] < -1e-6) or np.any(a[finite] > upper + 1e-5)):
            raise ValueError(f"{fname} values outside registered [0,{upper}] bounds")
        feats[key] = np.where(finite, np.clip(np.nan_to_num(a), 0.0, upper), 0.0).astype(np.float32)
    names = list(feats)
    return feats, names


def add_h29_5_interactions(feats: dict[str, np.ndarray], valid: np.ndarray) -> list[str]:
    """Add the preregistered persistence × strain × seismicity interactions in H29-5.

    Inputs are robust-scaled raw bands and corrected, bounded worm rasters. The product is a
    ranking feature for a held-out-zone classifier, not a probability or an inferred fault map.
    All interactions are zero where no joint level-0 potential-field edge was recorded.
    """
    required = {
        "worm_joint_persist", "worm_joint_defined", "worm_joint_strength_ratio",
        "raw_geod_2ndinv", "raw_geod_shearrate", "raw_geod_dilatationrate",
        "raw_deq_n100a15", "raw_ieq_n100a15",
    }
    missing = sorted(required - feats.keys())
    if missing:
        raise ValueError(f"H29-5 requires missing features: {', '.join(missing)}")
    valid = np.asarray(valid, bool)
    if any(feats[k].shape != valid.shape for k in required):
        raise ValueError("H29-5 input feature shapes must match valid mask")

    defined = (feats["worm_joint_defined"] > 0.5) & valid
    persistence = np.where(defined, np.clip(feats["worm_joint_persist"], 0.0, 1.0), 0.0)
    strength = np.where(defined, np.clip(feats["worm_joint_strength_ratio"] / 2.0, 0.0, 1.0), 0.0)
    structural = persistence * strength
    strain = np.maximum.reduce([
        np.clip(feats["raw_geod_2ndinv"], 0.0, 1.0),
        np.clip(feats["raw_geod_shearrate"], 0.0, 1.0),
        np.clip(feats["raw_geod_dilatationrate"], 0.0, 1.0),
    ])
    dep_eq = np.clip(feats["raw_deq_n100a15"], 0.0, 1.0)
    ind_eq = np.clip(feats["raw_ieq_n100a15"], 0.0, 1.0)
    seismic = np.sqrt(dep_eq * ind_eq)
    names = ["h29_5_worm_strain", "h29_5_worm_dep_eq", "h29_5_worm_ind_eq",
             "h29_5_corridor_interaction"]
    values = [structural * strain, structural * dep_eq, structural * ind_eq,
              structural * strain * seismic]
    for key, value in zip(names, values):
        feats[key] = np.where(valid, np.clip(value, 0.0, 1.0), 0.0).astype(np.float32)
    return names


def sample_rows(feats: dict[str, np.ndarray], names: list[str], sel_y: np.ndarray, sel_x: np.ndarray,
                label_arr: np.ndarray, sample_weight: np.ndarray | None = None):
    X = np.stack([feats[n][sel_y, sel_x] for n in names], axis=1).astype(np.float32)
    y = label_arr[sel_y, sel_x].astype(np.int8)
    return X, y, sample_weight


def dense_rows(feats: dict[str, np.ndarray], names: list[str], chunk: int = 500_000):
    """Yield (slice_index, X_chunk) row-chunks in raster order for dense prediction."""
    any_arr = next(iter(feats.values()))
    n = int(np.prod(any_arr.shape))
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        X = np.stack([feats[nm].reshape(-1)[s:e] for nm in names], axis=1).astype(np.float32)
        yield slice(s, e), X
