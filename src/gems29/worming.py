"""Multiscale upward-continuation edge persistence for potential fields.

For each field, Fourier upward-continuation is evaluated at fixed heights. At every height,
local maxima of the horizontal-gradient modulus are thresholded as candidate edges. A level-0 edge
is tracked through adjacent levels within a preregistered spatial tolerance. The normalized
persistence is the last matched level index divided by ``n_levels - 1``; it is consequently in
[0, 1], with 1 meaning survival through the full ladder. This is a structural proxy, not a unique
depth estimate and not proof that an edge is a fault.

The method follows Hornby, Boschetti & Horowitz (1999), “Analysis of potential field data in the
wavelet domain,” Geophysical Journal International 137(1), 175–196,
https://doi.org/10.1046/j.1365-246X.1999.00788.x, and is operationalized for interpretation by
Horowitz (2018, Stanford-GMC workshop). Upward continuation changes the potential-field scale; it
is not a generic Gaussian scale-space. The continuation ladder and edge-tracking choices here are
project-specific implementation decisions rather than a literal reproduction of the published
wavelet coefficients.

This implementation also records magnetic-edge strike summaries. It does not calculate a
frequency-domain flight-line notch or a spectral energy ratio; that is a separate, untested
hypothesis. The GeoDAWN flight-line spacing is documented in the USGS ScienceBase item
657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ.
"""

from __future__ import annotations

import numpy as np
from scipy import fft as spfft
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from . import paths

PIXEL_M = paths.GRID["pixel_m"]

# Continuation ladder in metres above the observation surface (h=0 is the raw grid).
LADDER_M = (0, 100, 200, 400, 800, 1600)
# Fraction of in-footprint HGM above which a cell counts as a candidate edge at that level.
EDGE_QUANTILE = 0.95
# Cross-level match tolerance growth, in pixels; a heuristic, not an inversion-derived uncertainty.
TOL_PX = 1.0
TOL_SLOPE_PX_PER_100M = 0.5
# Reliability threshold used by the pre-registered emission arm.
TAU_PERSIST = 0.5


def prep_field(values: np.ndarray, valid: np.ndarray, taper: int = 192) -> tuple[np.ndarray, np.ndarray]:
    """Fill invalid cells from nearest valid cell and apply a cosine edge taper (FFT hygiene)."""
    v = np.asarray(values, np.float32)
    mask = np.asarray(valid, bool)
    if v.ndim != 2 or mask.shape != v.shape:
        raise ValueError("values and valid must be same-shape 2-D arrays")
    if not mask.any():
        raise ValueError("field has no valid cells")
    if not np.isfinite(v[mask]).all():
        raise ValueError("valid field cells must be finite")
    if not mask.all():
        idx = distance_transform_edt(~mask, return_distances=False, return_indices=True)
        v = v[tuple(idx)]
    # Preserve the nearest-valid fill above; replacing those cells with a global median would
    # silently violate the preregistered FFT boundary treatment and create a different edge field.
    v = v.astype(np.float64, copy=False)
    v -= np.median(v[mask])
    H, W = v.shape
    t = np.ones(H, dtype=np.float64)
    if taper > 0 and taper * 2 < H:
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, taper))
        t[:taper] *= ramp
        t[H - taper:] *= ramp[::-1]
    w = np.ones(W, dtype=np.float64)
    if taper > 0 and taper * 2 < W:
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, taper))
        w[:taper] *= ramp
        w[W - taper:] *= ramp[::-1]
    return v * t[:, None] * w[None, :], mask


def upward_continue(tapered: np.ndarray, height_m: float, *, pixel_m: float = PIXEL_M) -> np.ndarray:
    """Fourier upward continuation of a potential field by ``height_m`` metres (same grid)."""
    if height_m < 0.0:
        raise ValueError("upward-continuation height must be non-negative")
    if pixel_m <= 0.0:
        raise ValueError("pixel_m must be positive")
    if height_m == 0.0:
        return tapered.copy()
    H, W = tapered.shape
    fy = spfft.fftfreq(H, d=pixel_m)[:, None]
    fx = spfft.rfftfreq(W, d=pixel_m)[None, :]
    k = np.sqrt(fy * fy + fx * fx)
    spec = spfft.rfft2(tapered)
    spec *= np.exp(-2.0 * np.pi * k * height_m)
    return spfft.irfft2(spec, s=(H, W))


def hgm(field: np.ndarray, *, pixel_m: float = PIXEL_M) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Horizontal-gradient magnitude via second-order central differences."""
    gy, gx = np.gradient(field, pixel_m, pixel_m, edge_order=2)
    return gx, gy, np.hypot(gx, gy)


def directional_max(mag: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Local maxima of ``mag`` along the gradient direction (edge-perpendicular profile crest)."""
    H, W = mag.shape
    n = np.maximum(np.hypot(gx, gy), 1e-12)
    uy, ux = gy / n, gx / n
    oy = np.rint(uy).astype(np.int64)
    ox = np.rint(ux).astype(np.int64)
    yy, xx = np.indices((H, W))
    yp, xp = np.clip(yy + oy, 0, H - 1), np.clip(xx + ox, 0, W - 1)
    ym, xm = np.clip(yy - oy, 0, H - 1), np.clip(xx - ox, 0, W - 1)
    return (mag >= mag[yp, xp]) & (mag >= mag[ym, xm])


def detect_edges(field: np.ndarray, valid: np.ndarray, *, pixel_m: float = PIXEL_M):
    """Return (edge_mask, gx, gy, mag), thresholding directional maxima over ``valid`` cells."""
    gx, gy, mag = hgm(field, pixel_m=pixel_m)
    if not np.asarray(valid, bool).any():
        raise ValueError("valid mask has no cells")
    thr = float(np.quantile(mag[valid], EDGE_QUANTILE))
    edge = directional_max(mag, gx, gy) & (mag >= thr) & valid
    return edge, gx, gy, mag


def worm_persistence(edge_levels: list[np.ndarray], mag_levels: list[np.ndarray],
                     yy0: np.ndarray, xx0: np.ndarray, valid: np.ndarray,
                     ladder_m: tuple[int, ...] = LADDER_M) -> dict:
    """Track each level-0 edge through the continuation ladder.

    The normalized persistence ``P`` is the final matched level index divided by ``n_levels - 1``.
    A six-level ladder therefore maps indices 0..5 to P values 0, .2, .4, .6, .8, 1.0. An edge
    lost at the first upward step has P=0; an edge surviving all levels has P=1. Matching must be
    contiguous and proceeds from the previous level's matched position. Strength retention is
    separately recorded as M(h_last)/M(h_0), clipped to [0, 2].
    """
    ladder = tuple(int(h) for h in ladder_m)
    if not edge_levels or len(edge_levels) != len(mag_levels) or len(edge_levels) != len(ladder):
        raise ValueError("edge_levels, mag_levels, and ladder_m must have the same nonzero length")
    if any(b <= a for a, b in zip(ladder, ladder[1:])):
        raise ValueError("ladder_m must be strictly increasing")
    shape = np.asarray(valid).shape
    if len(shape) != 2 or any(np.asarray(e).shape != shape for e in edge_levels) \
            or any(np.asarray(m).shape != shape for m in mag_levels):
        raise ValueError("valid, edge levels, and magnitude levels must share one 2-D shape")
    yy0, xx0 = np.asarray(yy0, dtype=np.int64), np.asarray(xx0, dtype=np.int64)
    if yy0.shape != xx0.shape or (yy0.size and (
            (yy0 < 0).any() or (xx0 < 0).any() or (yy0 >= shape[0]).any() or (xx0 >= shape[1]).any())):
        raise ValueError("level-0 edge coordinates are malformed or out of bounds")
    if yy0.size and not (np.asarray(edge_levels[0], bool)[yy0, xx0] & np.asarray(valid, bool)[yy0, xx0]).all():
        raise ValueError("starting coordinates must be valid level-0 edges")

    n0 = yy0.size
    level_idx = np.zeros(n0, np.int32)
    strength_ratio = np.ones(n0, np.float32)
    m0 = np.asarray(mag_levels[0], np.float32)[yy0, xx0]
    trees: list[cKDTree | None] = []
    pts: list[np.ndarray] = []
    for edge in edge_levels:
        y, x = np.nonzero(edge)
        points = np.column_stack([y, x]).astype(np.float64)
        pts.append(points)
        trees.append(cKDTree(points) if y.size else None)
    cur_y = yy0.astype(np.float64)
    cur_x = xx0.astype(np.float64)
    alive = np.ones(n0, bool)
    for lvl in range(1, len(edge_levels)):
        if not alive.any() or trees[lvl] is None:
            break
        height_delta_100m = (ladder[lvl] - ladder[0]) / 100.0
        tol = TOL_PX + TOL_SLOPE_PX_PER_100M * height_delta_100m
        q = np.column_stack([cur_y[alive], cur_x[alive]])
        dist, j = trees[lvl].query(q, k=1, distance_upper_bound=tol)
        hits = np.isfinite(dist)
        hit_idx = np.nonzero(alive)[0][hits]
        level_idx[hit_idx] = lvl
        cur_y2, cur_x2 = cur_y.copy(), cur_x.copy()
        cur_y2[hit_idx] = pts[lvl][j[hits], 0]
        cur_x2[hit_idx] = pts[lvl][j[hits], 1]
        cur_y, cur_x = cur_y2, cur_x2
        mlast = np.asarray(mag_levels[lvl], np.float32)[cur_y[hit_idx].astype(int), cur_x[hit_idx].astype(int)]
        with np.errstate(divide="ignore", invalid="ignore"):
            strength_ratio[hit_idx] = np.clip(mlast / np.maximum(m0[hit_idx], 1e-12), 0.0, 2.0)
        new_alive = np.zeros(n0, bool)
        new_alive[hit_idx] = True
        alive = new_alive

    denominator = len(edge_levels) - 1
    persistence = level_idx.astype(np.float32) / denominator if denominator else np.zeros(n0, np.float32)
    h_last = np.asarray([ladder[int(i)] for i in level_idx], dtype=np.float32)
    return {"level_idx": level_idx, "persistence": persistence,
            "strength_ratio": strength_ratio,
            "h_last_m": h_last}


def run_field(field_name: str, values: np.ndarray, valid: np.ndarray, *, out_dir,
              ladder_m: tuple[int, ...] = LADDER_M) -> dict:
    """Full worming pass on one potential field; writes rasters and returns statistics."""
    from . import gridio

    ladder = tuple(int(h) for h in ladder_m)
    if not ladder:
        raise ValueError("continuation ladder cannot be empty")
    tapered, mask = prep_field(values, valid)
    edges, mags = [], []
    gx0 = gy0 = None
    for h in ladder:
        cont = upward_continue(tapered, h)
        edge, gx, gy, mag = detect_edges(cont, mask)
        if h == 0:
            gx0, gy0 = gx.astype(np.float32), gy.astype(np.float32)
        edges.append(edge & mask)
        mags.append(mag.astype(np.float32))
    yy0, xx0 = np.nonzero(edges[0])
    stats = worm_persistence(edges, mags, yy0, xx0, mask, ladder)

    P = np.zeros(mask.shape, np.float32)
    Hlast = np.zeros(mask.shape, np.float32)
    Sr = np.zeros(mask.shape, np.float32)
    P[yy0, xx0] = stats["persistence"]
    Hlast[yy0, xx0] = stats["h_last_m"]
    Sr[yy0, xx0] = stats["strength_ratio"]
    E0 = edges[0].astype(np.uint8)

    # Orientation of each level-0 edge: strike = gradient direction + 90 degrees, 0..180.
    strike = np.full(mask.shape, np.nan, np.float32)
    gxn, gyn = gx0[edges[0]], gy0[edges[0]]
    strike[edges[0]] = ((np.degrees(np.arctan2(gyn, gxn)) + 90.0) % 180.0).astype(np.float32)

    tag = out_dir / f"worm_{field_name}"
    gridio.write_raster(P, tag.parent / f"{tag.name}_persist.tif", valid=mask)
    gridio.write_raster(Hlast, tag.parent / f"{tag.name}_hlast_m.tif", valid=mask)
    gridio.write_raster(Sr, tag.parent / f"{tag.name}_strength_ratio.tif", valid=mask)
    gridio.write_raster(E0, tag.parent / f"{tag.name}_edge0.tif", valid=mask, dtype="uint8")
    gridio.write_raster(strike, tag.parent / f"{tag.name}_strike.tif", valid=mask)

    n_edges = int(edges[0].sum())
    frac = lambda condition: float(np.mean(condition)) if n_edges else 0.0
    receipt = {
        "field": field_name, "ladder_m": list(ladder),
        "edge_quantile": EDGE_QUANTILE, "tol_px": TOL_PX,
        "tol_slope_px_per_100m": TOL_SLOPE_PX_PER_100M,
        "persistence_definition": "last_matched_level_index / (n_levels - 1); bounded [0,1]",
        "n_edges_level0": n_edges,
        "frac_edges_full_ladder": frac(stats["level_idx"] == len(ladder) - 1),
        "frac_edges_level0_only": frac(stats["level_idx"] == 0),
        "mean_persistence": frac(stats["persistence"]),
        "max_persistence": float(stats["persistence"].max()) if n_edges else 0.0,
        "max_strength_ratio": float(stats["strength_ratio"].max()) if n_edges else 0.0,
    }
    return {"P": P, "Hlast": Hlast, "Sr": Sr, "E0": E0, "strike": strike,
            "receipt": receipt, "mags_last": mags[-1]}


def line_audit(mag_out: dict, valid: np.ndarray) -> dict:
    """Summarize persistence by edge strike; this is not a frequency-domain artifact test."""
    strike = mag_out["strike"]
    P = mag_out["P"]
    edge = (mag_out["E0"] > 0) & np.asarray(valid, bool)
    # Strike is represented in [0,180); E-W strike is near 0/180, N-S near 90.
    ew = edge & np.isfinite(strike) & ((strike <= 15) | (strike >= 165))
    ns = edge & np.isfinite(strike) & (strike >= 75) & (strike <= 105)
    other = edge & np.isfinite(strike) & ~ew & ~ns
    return {
        "mean_persist_ew_strike": float(np.mean(P[ew])) if ew.any() else None,
        "mean_persist_ns_strike": float(np.mean(P[ns])) if ns.any() else None,
        "mean_persist_other": float(np.mean(P[other])) if other.any() else None,
        "n_ew": int(ew.sum()), "n_ns": int(ns.sum()), "n_other": int(other.sum()),
        "interpretation_limit": "strike summaries only; no spectral line-frequency energy, no notch, "
                                "and no claim that any individual E-W edge is an acquisition artifact",
    }


def uc_crosscheck(tmi: np.ndarray, up150_q: np.ndarray, valid: np.ndarray,
                  height_m: float = 150.0, reference_layer: str = "TMI_up150") -> dict:
    """Soft operator check against an owner-mirrored contractor upward-continuation grid.

    Compare rank correlations of horizontal-gradient magnitudes after applying our own continuation
    at ``height_m`` versus the u8-quantised contractor grid. This is not a byte comparison or a
    check against organizer-delivered data; quantisation and taper choices limit the inference.
    """
    _, _, mag_a = hgm(upward_continue(prep_field(tmi, valid)[0], height_m))
    from . import gridio
    deq = gridio.dequantize(up150_q.astype(np.float64), 1.0, "linear")
    _, _, mag_b = hgm(deq)
    from scipy.stats import spearmanr
    m = np.asarray(valid, bool) & (mag_a > 0) & (mag_b > 0)
    step = 4
    idx = np.nonzero(m[::step, ::step])
    rho = spearmanr(mag_a[::step, ::step][idx], mag_b[::step, ::step][idx]).statistic
    return {"spearman_hgm_ours_vs_contractor_up150": float(rho),
            "n_sampled_pixels": int(idx[0].size),
            "height_m": float(height_m), "reference_layer": reference_layer,
            "provenance": "owner-mirrored u8 contractor band; operator agreement is not source authentication"}
