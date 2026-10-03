"""Feature construction for families A-D (static) and E (per-draw, visible catalogue only).

All grids share the competition grid (3730 x 3292, EPSG:32611, 100 m). Static features are stored as
footprint-only float32 vectors in one memory map so that 60+ features fit a 4 GB machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    gaussian_laplace,
    maximum_filter,
    minimum_filter,
    uniform_filter,
    zoom,
)

from .families import family_columns

BASE_NAMES = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc", "geod_shearrate",
    "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg", "det_elev", "iso_grav_anom",
    "tmi", "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
]
LIDAR_BANDS = [
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max", "upface_max",
    "cross_max", "relief", "coh100", "strike", "valid",
]
LIDAR_QUANT = {  # name -> (xmax, transform) from lidar_scarp_features.json (owner mirror, 3DEP derived)
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"), "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def nearest_fill(a: np.ndarray) -> np.ndarray:
    """Fill NaNs with the nearest finite value (for filtering only; outputs are re-masked)."""
    bad = ~np.isfinite(a)
    if not bad.any():
        return a.astype(np.float32, copy=False)
    idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
    return a[tuple(idx)].astype(np.float32)


def grad_mag(a: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    gy, gx = np.gradient(gaussian_filter(a, sigma))
    return np.sqrt(gx * gx + gy * gy)


def ridge_strength(a: np.ndarray, sigma: float) -> np.ndarray:
    """Magnitude of the most negative Hessian eigenvalue (crest/worm line strength), >= 0."""
    s = gaussian_filter(a, sigma)
    gy, gx = np.gradient(s)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    hxy = 0.5 * (hxy + hyx)
    lam = 0.5 * (hxx + hyy) - np.sqrt(((hxx - hyy) * 0.5) ** 2 + hxy**2)
    return np.maximum(-lam, 0.0).astype(np.float32)


def dequantize(q: np.ndarray, xmax: float, how: str) -> np.ndarray:
    """Invert q = 1 + round(254 t(x/xmax)); q == 0 means no data -> NaN."""
    t = (q.astype(np.float32) - 1.0) / 254.0
    x = xmax * (t * t if how == "sqrt" else t)
    return np.where(q > 0, x, np.nan).astype(np.float32)


def load_base(band_dir: Path) -> dict[str, np.ndarray]:
    out = {}
    for i, n in enumerate(BASE_NAMES, 1):
        out[n] = np.load(band_dir / f"{i:02d}_{n}.npy", mmap_mode="r")
    return out


# ----------------------------------------------------------------------------------------------
# static families
# ----------------------------------------------------------------------------------------------
def build_static(
    band_dir: Path,
    footprint: np.ndarray,
    external_dir: Path,
    out_path: Path,
    families: str = "ABCD",
) -> list[str]:
    """Compute all static feature grids and write a (n_feat, n_footprint) float32 memmap + names JSON."""
    base = load_base(band_dir)
    foot = np.asarray(footprint, bool)
    fi = np.flatnonzero(foot.ravel())
    names: list[str] = []
    for f in families:
        names += family_columns(f)
    mm = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32, shape=(len(names), fi.size))
    col = {n: i for i, n in enumerate(names)}

    def put(name: str, grid: np.ndarray) -> None:
        if name in col:
            mm[col[name]] = np.asarray(grid, np.float32).ravel()[fi]

    filled: dict[str, np.ndarray] = {}

    def fl(n: str) -> np.ndarray:
        if n not in filled:
            filled[n] = nearest_fill(np.asarray(base[n]))
        return filled[n]

    # base bands (raw values; NaN where the raster has nodata)
    for n in BASE_NAMES:
        put(n, np.asarray(base[n]))

    # ---- A: potential-field gradients ------------------------------------------------------
    if "A" in families:
        hg, vg = fl("tmi_hg"), fl("tmi_vg")
        put("A_mag_as", np.log1p(np.sqrt(hg**2 + vg**2)))
        put("A_mag_tilt", np.arctan2(vg, hg))
        ghg, gvg = fl("iso_grav_anom_hg"), fl("iso_grav_anom_vg")
        put("A_grav_as", np.log1p(np.sqrt(ghg**2 + gvg**2)))
        put("A_grav_tilt", np.arctan2(gvg, np.abs(ghg) + 1e-9))
        put("A_mag_hg_ridge", ridge_strength(np.log1p(hg), 1.5))
        put("A_grav_hg_ridge", ridge_strength(ghg, 1.5))
        put("A_mag_hg_ctx", np.log1p(hg) - np.log1p(uniform_filter(hg, 21)))
        del hg, vg, ghg, gvg
        filled.clear()

    # ---- B: DEM curvature / scarp ----------------------------------------------------------
    if "B" in families:
        z = fl("det_elev")
        put("B_lap1", gaussian_laplace(z, 1.0))
        put("B_lap2", gaussian_laplace(z, 2.0))
        put("B_tpi5", z - uniform_filter(z, 5))
        put("B_tpi11", z - uniform_filter(z, 11))
        put("B_relief5", maximum_filter(z, 5) - minimum_filter(z, 5))
        sl = fl("det_elev_slope")
        put("B_slope_grad", grad_mag(sl, 1.0))
        put("B_slope_ctx", sl - uniform_filter(sl, 9))
        put("B_crest", ridge_strength(z, 1.5))
        put("B_trough", ridge_strength(-z, 1.5))
        del z, sl
        filled.clear()
        with rasterio.open(external_dir / "lidar_scarp_features_u8.tif") as s:
            q = s.read()
        lid = {n: dequantize(q[i], *LIDAR_QUANT[n]) for i, n in enumerate(LIDAR_BANDS)}
        for n in LIDAR_BANDS:
            if n == "strike":
                th = np.deg2rad(lid[n])
                put("L_strike_c2", np.cos(2 * th))
                put("L_strike_s2", np.sin(2 * th))
            else:
                put(f"L_{n}", lid[n])
        del q, lid

    # ---- C: strain / seismicity ------------------------------------------------------------
    if "C" in families:
        put("C_2ndinv_grad", grad_mag(fl("geod_2ndinv"), 2.0))
        put("C_shear_grad", grad_mag(fl("geod_shearrate"), 2.0))
        filled.clear()

    # ---- D: thermal / geochemical ----------------------------------------------------------
    if "D" in families:
        put("D_cond_grad", grad_mag(fl("cond_surf"), 1.0))
        put("D_depth_base_grad", grad_mag(np.log1p(np.maximum(fl("depth_to_base_surf"), 0)), 1.0))
        filled.clear()
        with rasterio.open(external_dir / "geodawn_rad_u8.tif") as s:
            rad = s.read()
        with rasterio.open(external_dir / "geodawn_extensions_u8.tif") as s:
            ext = s.read()
        rk = {n: np.where(rad[i] > 0, rad[i].astype(np.float32), np.nan) for i, n in enumerate(["K", "Th", "U"])}
        for n in ("K", "Th", "U"):
            put(f"D_{n}", rk[n])
        for i, n in enumerate(["ThK", "UK", "UTh"]):
            put(f"D_{n}", np.where(ext[i] > 0, ext[i].astype(np.float32), np.nan))
        for n in ("ThK", "UK"):
            i = ["ThK", "UK", "UTh"].index(n)
            put(f"D_{n}_edge", grad_mag(nearest_fill(np.where(ext[i] > 0, ext[i].astype(np.float32), np.nan)), 1.0))
        del rad, ext, rk
        _gdr_features(external_dir / "gdr_wellspring_in_footprint.csv", foot.shape, put)

    mm.flush()
    Path(str(out_path) + ".names.json").write_text(json.dumps(names))
    return names


def _gdr_features(csv_path: Path, shape: tuple, put) -> None:
    """GDR 1391 spring / well points -> proximity, density and max-temperature rasters.

    ``dist_known_fault_px`` in the CSV is label-derived and is deliberately NOT used.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)
    df = df[(df.row >= 0) & (df.row < shape[0]) & (df.col >= 0) & (df.col < shape[1])]
    r, c = df.row.to_numpy(), df.col.to_numpy()
    cnt = np.zeros(shape, np.float32)
    np.add.at(cnt, (r, c), 1.0)
    hot = np.zeros(shape, bool)
    hot[r[(df.thermalclass.str.strip() == "Hot").to_numpy()], c[(df.thermalclass.str.strip() == "Hot").to_numpy()]] = True
    tmax = np.full(shape, np.nan, np.float32)
    t = df.temp_c.to_numpy(dtype=float)
    ok = np.isfinite(t)
    tt = np.zeros(shape, np.float32)
    np.maximum.at(tt, (r[ok], c[ok]), t[ok].astype(np.float32))
    tmax = np.where(tt > 0, tt, np.nan)
    q = df.geothermquartz_c.to_numpy(dtype=float)
    okq = np.isfinite(q)
    qq = np.full(shape, -1e9, np.float32)
    np.maximum.at(qq, (r[okq], c[okq]), q[okq].astype(np.float32))
    qgrid = np.where(qq > -1e8, qq, np.nan)
    put("D_gdr_dist_hot", np.minimum(distance_transform_edt(~hot), 150.0))
    put("D_gdr_kde2km", np.log1p(gaussian_filter(cnt, 20.0) * (2 * np.pi * 20.0**2)))
    w = 51  # 5 km half-window ~ 51 px square
    put("D_gdr_tmax5km", maximum_filter(np.nan_to_num(tmax, nan=-1.0), size=w))
    put("D_gdr_quartz5km", maximum_filter(np.nan_to_num(qgrid, nan=-100.0), size=w))


# ----------------------------------------------------------------------------------------------
# family E: catalogue geometry from the VISIBLE known faults only
# ----------------------------------------------------------------------------------------------
def _coarse_density(mask: np.ndarray, sigma_px: float, f: int = 4) -> np.ndarray:
    H, W = mask.shape
    Hc, Wc = H // f, W // f
    m = mask[: Hc * f, : Wc * f].astype(np.float32).reshape(Hc, f, Wc, f).mean(axis=(1, 3))
    g = gaussian_filter(m, sigma_px / f)
    up = zoom(g, f, order=1)
    out = np.zeros((H, W), np.float32)
    out[: up.shape[0], : up.shape[1]] = up[:H, :W]
    return out


def build_catalogue_features(visible: np.ndarray, footprint_idx: np.ndarray) -> np.ndarray:
    """Return (7, n_footprint) float32 for names in ``families.FAMILIES['E']['derived']``."""
    v = np.asarray(visible, bool)
    H, W = v.shape
    dist, (iy, ix) = distance_transform_edt(~v, return_indices=True)
    # local orientation of the visible faults: doubled-angle structure tensor of the smoothed mask
    s = gaussian_filter(v.astype(np.float32), 2.0)
    gy, gx = np.gradient(s)
    jxx, jyy, jxy = gaussian_filter(gx * gx, 2.0), gaussian_filter(gy * gy, 2.0), gaussian_filter(gx * gy, 2.0)
    th_grad2 = np.arctan2(2 * jxy, jxx - jyy)  # doubled gradient angle; the line is perpendicular
    c2, s2 = -np.cos(th_grad2), -np.sin(th_grad2)
    del gx, gy, jxx, jyy, jxy, th_grad2, s
    near_c2, near_s2 = c2[iy, ix], s2[iy, ix]
    del iy, ix
    # orientation coherence within ~2 km (resultant length of doubled-angle vectors over visible pixels)
    wv = v.astype(np.float32)
    sc, ss, sw = (_coarse_density(wv * c2, 20.0), _coarse_density(wv * s2, 20.0), _coarse_density(wv, 20.0))
    coh = np.sqrt(sc * sc + ss * ss) / np.maximum(sw, 1e-6)
    coh = np.where(sw > 1e-5, np.minimum(coh, 1.0), 0.0)
    feats = [
        np.log1p(np.minimum(dist, 60.0)),
        near_c2,
        near_s2,
        gaussian_filter(wv, 5.0),
        _coarse_density(wv, 20.0),
        _coarse_density(wv, 50.0),
        coh,
    ]
    out = np.empty((len(feats), footprint_idx.size), np.float32)
    for i, g in enumerate(feats):
        out[i] = np.asarray(g, np.float32).ravel()[footprint_idx]
    return out


def build_tip_continuation(visible: np.ndarray, footprint: np.ndarray, footprint_idx: np.ndarray,
                           chunk_size: int = 500_000) -> np.ndarray:
    """Directed continuation strength beyond endpoints of the *visible* catalogue.

    Endpoints are degree-1 pixels in the 8-neighbour graph, with full local footprint support. Their outward
    vector points away from the sole visible neighbour. For each footprint cell, the nearest endpoint must be
    1.5--12 pixels away, locally coherent, line-parallel and outward-facing. The output is a [0, 1] vector.
    Calculations are chunked after the distance transform to bound temporary memory on the 4 GB runner.
    """
    from scipy.ndimage import binary_erosion, convolve, distance_transform_edt

    v = np.asarray(visible, dtype=bool).copy()
    foot = np.asarray(footprint, dtype=bool)
    raw_fi = np.asarray(footprint_idx)
    if v.ndim != 2 or foot.shape != v.shape or raw_fi.ndim != 1:
        raise ValueError("visible, footprint, and footprint_idx must describe one aligned 2-D grid")
    if raw_fi.size and not np.issubdtype(raw_fi.dtype, np.integer):
        raise ValueError("footprint_idx must contain integer flat indices")
    fi = raw_fi.astype(np.int64, copy=False)
    H, W = v.shape
    if isinstance(chunk_size, (bool, np.bool_)) or not isinstance(chunk_size, (int, np.integer)) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if fi.size and ((fi < 0).any() or (fi >= H * W).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only valid flat indices inside the footprint")
    v &= foot
    out = np.zeros(fi.size, np.float32)
    if not v.any() or not fi.size:
        return out

    # Do not treat a catalogue line clipped at the grid/footprint edge as a geological tip.
    full_3x3 = binary_erosion(foot, structure=np.ones((3, 3), bool), border_value=0)
    kernel = np.ones((3, 3), np.uint8)
    kernel[1, 1] = 0
    degree = convolve(v.astype(np.uint8), kernel, mode="constant", cval=0)
    tips = v & (degree == 1) & full_3x3
    tip_r, tip_c = np.nonzero(tips)
    if not tip_r.size:
        return out

    # Doubled-angle local strike matches family E; coherence is its 2 km resultant length (also family E).
    smooth = gaussian_filter(v.astype(np.float32), 2.0)
    gy, gx = np.gradient(smooth)
    jxx = gaussian_filter(gx * gx, 2.0)
    jyy = gaussian_filter(gy * gy, 2.0)
    jxy = gaussian_filter(gx * gy, 2.0)
    phi2 = np.arctan2(2.0 * jxy, jxx - jyy)
    line_c2 = -np.cos(phi2).astype(np.float32)
    line_s2 = -np.sin(phi2).astype(np.float32)
    wv = v.astype(np.float32)
    sc, ss, sw = (_coarse_density(wv * line_c2, 20.0), _coarse_density(wv * line_s2, 20.0), _coarse_density(wv, 20.0))
    coherence = np.sqrt(sc * sc + ss * ss) / np.maximum(sw, 1e-6)
    coherence = np.where(sw > 1e-5, np.minimum(coherence, 1.0), 0.0)
    tip_c2 = line_c2[tip_r, tip_c]
    tip_s2 = line_s2[tip_r, tip_c]
    tip_coh = coherence[tip_r, tip_c].astype(np.float32)
    del smooth, gy, gx, jxx, jyy, jxy, phi2, line_c2, line_s2, wv, sc, ss, sw, coherence, degree, full_3x3

    # A degree-1 endpoint has one visible neighbour. Point its direction away from that pixel.
    tip_out_r = np.zeros(tip_r.size, np.float32)
    tip_out_c = np.zeros(tip_c.size, np.float32)
    for i, (r, c) in enumerate(zip(tip_r.tolist(), tip_c.tolist(), strict=True)):
        nr = nc = -1
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and v[rr, cc]:
                    nr, nc = rr, cc
                    break
            if nr >= 0:
                break
        if nr < 0:
            continue
        orow, ocol = float(r - nr), float(c - nc)
        norm = float(np.hypot(orow, ocol))
        tip_out_r[i], tip_out_c[i] = orow / norm, ocol / norm

    # Nearest-tip indices are only 2 int32 grids (~98 MB); all per-pixel arithmetic is chunked.
    nearest = distance_transform_edt(~tips, return_distances=False, return_indices=True)
    tip_flat = tip_r.astype(np.int64) * W + tip_c.astype(np.int64)
    for start in range(0, fi.size, chunk_size):
        stop = min(fi.size, start + chunk_size)
        ids = fi[start:stop]
        rr = (ids // W).astype(np.int32)
        cc = (ids % W).astype(np.int32)
        nr = nearest[0, rr, cc]
        nc = nearest[1, rr, cc]
        dr = rr.astype(np.float32) - nr.astype(np.float32)
        dc = cc.astype(np.float32) - nc.astype(np.float32)
        d2 = dr * dr + dc * dc
        dist = np.sqrt(d2)
        near_flat = nr.astype(np.int64) * W + nc.astype(np.int64)
        ti = np.searchsorted(tip_flat, near_flat)
        safe_d2 = np.maximum(d2, 1e-12)
        cos2 = (dc * dc - dr * dr) / safe_d2
        sin2 = (2.0 * dc * dr) / safe_d2
        parallel = tip_c2[ti] * cos2 + tip_s2[ti] * sin2
        outward = dr * tip_out_r[ti] + dc * tip_out_c[ti]
        outward = outward / np.maximum(dist, 1e-12)
        align = np.clip((parallel - 0.5) / 0.5, 0.0, 1.0)
        forward = np.clip((outward - 0.5) / 0.5, 0.0, 1.0)
        strength = np.exp(-dist / 5.0) * align * forward * tip_coh[ti]
        valid = (dist >= 1.5) & (dist <= 12.0) & (tip_coh[ti] >= 0.25) & (parallel >= 0.5) & (outward >= 0.5)
        out[start:stop] = np.where(valid, np.clip(strength, 0.0, 1.0), 0.0)
    return out


# ----------------------------------------------------------------------------------------------
# add-on static columns for the pre-registered hypothesis tests (H26-1, H26-2)
# ----------------------------------------------------------------------------------------------
ADDON_NAMES = ["X1_K", "X1_ThK", "X1_UK", "S_dem_c2", "S_dem_s2"]


def build_addons(band_dir: Path, footprint: np.ndarray, external_dir: Path, out_path: Path, sep_px: float = 3.0) -> list[str]:
    """H26-1: |v(x+3n) - v(x-3n)| of K, Th/K, U/K across the 100 m DEM gradient normal ``n``.

    H26-2 ingredient: doubled-angle components of the DEM *line* direction (perpendicular to the gradient), same
    convention as the visible-catalogue orientation in :func:`build_catalogue_features` (x = column, y = row).
    """
    from scipy.ndimage import map_coordinates

    foot = np.asarray(footprint, bool)
    fi = np.flatnonzero(foot.ravel())
    z = nearest_fill(np.load(band_dir / "12_det_elev.npy"))
    zs = gaussian_filter(z, 1.5)
    gy, gx = np.gradient(zs)
    jxx, jyy, jxy = gaussian_filter(gx * gx, 2.0), gaussian_filter(gy * gy, 2.0), gaussian_filter(gx * gy, 2.0)
    phi2 = np.arctan2(2 * jxy, jxx - jyy)  # doubled gradient angle
    phi = 0.5 * phi2
    nx, ny = np.cos(phi).astype(np.float32), np.sin(phi).astype(np.float32)
    c2, s2 = (-np.cos(phi2)).astype(np.float32), (-np.sin(phi2)).astype(np.float32)
    del gx, gy, jxx, jyy, jxy, zs, z
    with rasterio.open(external_dir / "geodawn_rad_u8.tif") as s:
        k = s.read(1)
    with rasterio.open(external_dir / "geodawn_extensions_u8.tif") as s:
        thk, uk = s.read(1), s.read(2)
    fields = {"X1_K": k, "X1_ThK": thk, "X1_UK": uk}
    H, W = foot.shape
    mm = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32, shape=(len(ADDON_NAMES), fi.size))
    for j, nm in enumerate(ADDON_NAMES):
        if nm in fields:
            f = nearest_fill(np.where(fields[nm] > 0, fields[nm].astype(np.float32), np.nan))
            res = np.empty((H, W), np.float32)
            for r0 in range(0, H, 400):
                r1 = min(H, r0 + 400)
                rows, cols = np.mgrid[r0:r1, 0:W].astype(np.float32)
                plus = map_coordinates(f, [rows + sep_px * ny[r0:r1], cols + sep_px * nx[r0:r1]], order=1, mode="nearest")
                minus = map_coordinates(f, [rows - sep_px * ny[r0:r1], cols - sep_px * nx[r0:r1]], order=1, mode="nearest")
                res[r0:r1] = np.abs(plus - minus)
            mm[j] = uniform_filter(res, 3).ravel()[fi]
        elif nm == "S_dem_c2":
            mm[j] = c2.ravel()[fi]
        elif nm == "S_dem_s2":
            mm[j] = s2.ravel()[fi]
    mm.flush()
    Path(str(out_path) + ".names.json").write_text(json.dumps(ADDON_NAMES))
    return ADDON_NAMES
