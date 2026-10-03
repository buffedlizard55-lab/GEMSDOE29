"""H43: drainage-network organization — stream-power residual and knickpoint excess.

Frozen in ``knowledge/27_preregistered_h43_screen_2026-10-03.md``; designed in
``knowledge/25_candidates_v4_2026-10-03.md`` (rank 1 of the v4 slate).

Object
------
Every existing topographic channel in this repository (`B_*`, `L_*`, `S_*`, `H27`, `H30`) is a *local-window*
operator on the 100 m or derived LiDAR grids. Drainage organization is a *catchment-network* property:
whether a pixel carries a channel (`A >= 25` cells = 2.5 km^2), its unit stream power (`Omega = A^m S`), and
whether its local gradient exceeds the smooth concave equilibrium profile (`S propto A^-theta`) of its
drainage basin (a knickpoint / range-front steepness anomaly) depend on the entire upslope catchment. In
extending Basin-and-Range half-grabens, active range-front and relay faults pin knickpoints and focus stream
power along footwall/hanging-wall transitions that local curvature filters cannot separate from short hillslope
roughness.

Pipeline
--------
1. ``fill_dem(elev, valid)`` — priority-flood depression filling (Barnes, Lehman & Mulla 2014, *Computers &
   Geosciences* 62:117-127, doi:10.1016/j.cageo.2013.04.024) using a binary min-heap for rising terrain and a
   FIFO queue (guarded by ``pit[0] <= heap[0]``) for depressions, with a 1-pixel sentinel ring so flat-index
   8-neighbour steps never wrap across rows. Internal non-finite pixels inside ``valid`` (3,061 pixels in
   ``12_det_elev.npy``, ``IR-29-FOOTPRINT-DIFF``) are nearest-valid filled before flooding; only the outer
   boundary of ``valid`` seeds the outlets, without touching the fault catalogue.
2. ``d8_order(elev_filled, valid)`` — D8 steepest-descent routing (`(z_c - z_n) / dist` across 8 neighbours,
   cardinal distance 1, diagonal distance sqrt(2)) ordered by descending filled elevation (`np.argsort`),
   accumulating 1.0 cell per valid pixel downslope to the boundary outlets and propagating each outlet's
   basin ID upslope in a single reverse pass.
3. ``stream_power(acc, slope, m=0.5)`` on a 3-pixel Gaussian pre-smoothed gradient magnitude (nearest-valid
   padded outside ``valid`` so the footprint edge has no artificial cliff), plus a per-basin Theil-Sen /
   repeated-median log-log fit of ``log10(slope)`` on ``log10(area)`` over channel pixels (``acc >= 25``
   cells; basins with ``>= 200`` channel pixels get their own fit, smaller edge basins use the global
   footprint channel fit).
4. Five footprint-aligned columns in ``[0, 1]``:
   - ``H43_LNACC``: ``log10(acc)`` scaled by its 99.9th footprint percentile.
   - ``H43_OMEGA``: stream power ``A^0.5 * S`` scaled between its 1st and 99th footprint percentiles.
   - ``H43_KNICK``: positive log-slope residual above the basin envelope on ``acc >= 25`` channels, clipped
     at its 95th positive percentile and scaled to ``[0, 1]``.
   - ``H43_OFF_FRONT``: ``H43_KNICK`` restricted to pixels ``>= 500 m`` (5 px) from every *visible* catalogue
     pixel for the current draw (an active knickpoint front with no mapped fault trace).
   - ``H43_CHANNEL_SCARP``: ``H43_OMEGA * h27_scarp`` (stream-power anomaly co-located with a scarp step).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
from typing import Any

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt, gaussian_filter

H43_NAMES = ["H43_LNACC", "H43_OMEGA", "H43_KNICK", "H43_OFF_FRONT", "H43_CHANNEL_SCARP"]

# Frozen parameters (knowledge/25 section H43 and knowledge/27 section 2). Grid spacing is 100 m (1 px = 100 m).
H43_PARAMS: dict[str, float] = dict(
    pit_eps=1e-6,                # monotone increment per step across flat/depression cells during priority-flood
    slope_smooth_sigma_px=3.0,   # 3-pixel Gaussian pre-smoothing before np.gradient local slope
    stream_power_m=0.5,          # area exponent m in Omega = A^m * S
    min_channel_acc_px=25.0,     # 25 cells = 2.5 km^2 catchment threshold for channel / knickpoint validity
    min_basin_channel_px=200.0,  # minimum channel pixels in a single outlet basin for a per-basin log-log fit
    knick_clip_pct=95.0,         # positive log-slope residual clipped at its 95th percentile
    off_catalogue_min_px=5.0,    # off-catalogue = >= 500 m (5 px) from every visible catalogue pixel
    lnacc_scale_pct=99.9,        # percentile of log10(acc) used to scale H43_LNACC into [0, 1]
    omega_lo_pct=1.0,            # lower percentile for H43_OMEGA scaling
    omega_hi_pct=99.0,           # upper percentile for H43_OMEGA scaling
    slope_floor=1e-4,            # numerical floor on slope before log10 in the S-A regression
)


@dataclass
class DrainageField:
    """Draw-independent H43 grids computed once per run from the cached DEM and footprint."""

    lnacc_grid: np.ndarray     # float32 (H, W) in [0, 1], zero outside footprint
    omega_grid: np.ndarray     # float32 (H, W) in [0, 1], zero outside footprint
    knick_grid: np.ndarray     # float32 (H, W) in [0, 1], zero outside footprint
    diagnostics: dict[str, Any]


def _nearest_fill_2d(arr: np.ndarray, valid_finite: np.ndarray) -> np.ndarray:
    """Fill non-finite / outside cells from the nearest valid finite cell (no global-median step)."""
    if valid_finite.all():
        return np.asarray(arr, np.float64).copy()
    if not valid_finite.any():
        raise ValueError("cannot nearest-fill an array with zero valid finite cells")
    idx = distance_transform_edt(~valid_finite, return_distances=False, return_indices=True)
    return np.asarray(arr[tuple(idx)], np.float64)


def fill_dem(elev: np.ndarray, valid: np.ndarray | None = None, *, eps: float = H43_PARAMS["pit_eps"]) -> np.ndarray:
    """Priority-flood depression filling over a 2-D DEM grid.

    Boundary cells of ``valid`` (8-connected erosion border) seed the priority queue so every interior cell
    drains strictly toward the domain boundary. Internal NaNs inside ``valid`` are filled from their nearest
    finite ``valid`` cell before flooding. Returns a ``float64`` array equal to ``np.nan`` outside ``valid``
    and satisfying ``filled >= elev_nearest`` everywhere inside ``valid``.
    """
    z_in = np.asarray(elev, np.float64)
    if z_in.ndim != 2:
        raise ValueError("elev must be a 2-D array")
    if eps < 0 or not np.isfinite(eps):
        raise ValueError("eps must be a non-negative finite float")
    val = np.isfinite(z_in) if valid is None else np.asarray(valid, bool)
    if val.shape != z_in.shape:
        raise ValueError("valid mask must match elev shape")
    if not val.any():
        raise ValueError("valid mask is empty")

    finite = val & np.isfinite(z_in)
    z_nn = _nearest_fill_2d(z_in, finite)
    z_work = np.where(val, z_nn, np.nan)

    # 1-pixel sentinel ring prevents 1-D neighbour offsets from wrapping across rows or leaving the array.
    z_pad = np.pad(z_work, 1, mode="constant", constant_values=np.nan)
    v_pad = np.pad(val, 1, mode="constant", constant_values=False)
    Hp, Wp = z_pad.shape
    interior = binary_erosion(v_pad, structure=np.ones((3, 3), bool), border_value=0)
    b_idx = np.flatnonzero(v_pad & ~interior)

    out = z_pad.ravel().copy()
    v_flat = v_pad.ravel()
    visited = ~v_flat.copy()
    visited[b_idx] = True

    heap: list[tuple[float, int]] = [(float(out[i]), int(i)) for i in b_idx]
    heapq.heapify(heap)
    pit: deque[tuple[float, int]] = deque()
    offsets = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)

    heappop = heapq.heappop
    heappush = heapq.heappush
    pit_pop = pit.popleft
    pit_push = pit.append
    step_eps = float(eps)

    while heap or pit:
        if pit and (not heap or pit[0][0] <= heap[0][0]):
            zc, c = pit_pop()
        else:
            zc, c = heappop(heap)
        for off in offsets:
            nb = c + off
            if not visited[nb]:
                visited[nb] = True
                zn = out[nb]
                if zn <= zc:
                    zn_new = zc + step_eps
                    out[nb] = zn_new
                    pit_push((zn_new, nb))
                else:
                    heappush(heap, (zn, nb))

    return out.reshape(Hp, Wp)[1:-1, 1:-1].copy()


def d8_order(
    elev_filled: np.ndarray,
    valid: np.ndarray | None = None,
    *,
    return_basins: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray, np.ndarray]:
    """D8 steepest-descent flow accumulation from a depression-filled DEM.

    Each valid cell starts with 1.0 unit of area and hands its accumulated area to its steepest downslope
    8-neighbour (`(z_c - z_n) / dist`, cardinal `dist=1`, diagonal `dist=sqrt(2)`), processed in descending
    elevation order (`np.argsort`). Boundary cells of ``valid`` are outlets (`receiver = self`) so water never
    leaks into invalid padding before reaching the boundary, and total area across outlets equals the number of
    valid cells. When ``return_basins=True``, returns ``(acc, basin_id, outlet_mask)``.
    """
    zf = np.asarray(elev_filled, np.float64)
    if zf.ndim != 2:
        raise ValueError("elev_filled must be a 2-D array")
    val = np.isfinite(zf) if valid is None else np.asarray(valid, bool)
    if val.shape != zf.shape:
        raise ValueError("valid mask must match elev_filled shape")
    if not val.any():
        raise ValueError("valid mask is empty")
    if not np.isfinite(zf[val]).all():
        raise ValueError("elev_filled contains non-finite values inside valid mask; call fill_dem first")

    v_pad = np.pad(val, 1, mode="constant", constant_values=False)
    f_pad = np.pad(np.where(val, zf, np.inf), 1, mode="constant", constant_values=np.inf)
    Hp, Wp = f_pad.shape
    interior = binary_erosion(v_pad, structure=np.ones((3, 3), bool), border_value=0)

    dy = (-1, -1, -1, 0, 0, 1, 1, 1)
    dx = (-1, 0, 1, -1, 1, -1, 0, 1)
    dists = np.hypot(dy, dx)
    offsets = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)

    best_slope = np.zeros((Hp, Wp), dtype=np.float64)
    best_off = np.zeros((Hp, Wp), dtype=np.int32)
    center = f_pad[1:-1, 1:-1]
    with np.errstate(invalid="ignore"):
        for d_y, d_x, dist, off in zip(dy, dx, dists, offsets):
            nb_z = f_pad[1 + d_y : Hp - 1 + d_y, 1 + d_x : Wp - 1 + d_x]
            s = (center - nb_z) / dist
            better = s > best_slope[1:-1, 1:-1]
            best_slope[1:-1, 1:-1] = np.where(better, s, best_slope[1:-1, 1:-1])
            best_off[1:-1, 1:-1] = np.where(better, off, best_off[1:-1, 1:-1])

    # Boundary cells of valid drain off the domain and act as terminal outlets.
    best_off[~interior] = 0
    v_flat = v_pad.ravel()
    f_flat = f_pad.ravel()
    valid_idx = np.flatnonzero(v_flat)
    # Stable mergesort preserves deterministic tie-breaking by raster order when two cells have equal z.
    order = valid_idx[np.argsort(f_flat[valid_idx], kind="mergesort")[::-1]]
    recv_all = np.arange(Hp * Wp, dtype=np.int32)
    recv_all[valid_idx] = valid_idx + best_off.ravel()[valid_idx]

    acc_pad = np.zeros(Hp * Wp, dtype=np.float64)
    acc_pad[valid_idx] = 1.0
    for c in order:
        r = recv_all[c]
        if r != c:
            acc_pad[r] += acc_pad[c]

    acc = acc_pad.reshape(Hp, Wp)[1:-1, 1:-1].copy()
    if not return_basins:
        return acc

    basin_pad = np.arange(Hp * Wp, dtype=np.int32)
    for c in order[::-1]:
        r = recv_all[c]
        if r != c:
            basin_pad[c] = basin_pad[r]
    basin = basin_pad.reshape(Hp, Wp)[1:-1, 1:-1].copy()
    basin[~val] = -1
    outlet_mask = (best_off[1:-1, 1:-1] == 0) & val
    return acc, basin, outlet_mask


def smoothed_slope(
    elev: np.ndarray,
    valid: np.ndarray | None = None,
    *,
    sigma_px: float = H43_PARAMS["slope_smooth_sigma_px"],
) -> np.ndarray:
    """Gradient magnitude of a Gaussian-smoothed, nearest-valid-padded elevation grid."""
    z_in = np.asarray(elev, np.float64)
    if z_in.ndim != 2:
        raise ValueError("elev must be a 2-D array")
    val = np.isfinite(z_in) if valid is None else np.asarray(valid, bool)
    finite = val & np.isfinite(z_in)
    z_nn = _nearest_fill_2d(z_in, finite)
    z_sm = gaussian_filter(z_nn, sigma=float(sigma_px), mode="nearest") if sigma_px > 0 else z_nn
    gy, gx = np.gradient(z_sm)
    slope = np.hypot(gy, gx)
    return np.where(val, slope, 0.0)


def stream_power(acc: np.ndarray, slope: np.ndarray, *, m: float = H43_PARAMS["stream_power_m"]) -> np.ndarray:
    """Stream-power index ``Omega = A^m * S`` with non-negative clipping."""
    a = np.asarray(acc, np.float64)
    s = np.asarray(slope, np.float64)
    if a.shape != s.shape:
        raise ValueError("acc and slope must have the same shape")
    if m <= 0 or not np.isfinite(m):
        raise ValueError("m must be a positive finite float")
    return np.power(np.maximum(a, 0.0), float(m)) * np.maximum(s, 0.0)


def repeated_median_log_fit(log_area: np.ndarray, log_slope: np.ndarray, *, n_bins: int = 16) -> tuple[float, float]:
    """Theil-Sen / repeated-median fit ``log_slope = b0 + b1 * log_area`` across quantile bins of ``log_area``."""
    x = np.asarray(log_area, np.float64).ravel()
    y = np.asarray(log_slope, np.float64).ravel()
    if x.size != y.size or x.size == 0:
        raise ValueError("log_area and log_slope must be non-empty 1-D arrays of equal length")
    qs = np.linspace(0.0, 100.0, int(n_bins) + 1)
    edges = np.percentile(x, qs)
    bx: list[float] = []
    by: list[float] = []
    for k in range(int(n_bins)):
        if k == int(n_bins) - 1:
            m = (x >= edges[k]) & (x <= edges[k + 1])
        else:
            m = (x >= edges[k]) & (x < edges[k + 1])
        if int(m.sum()) >= 5:
            bx.append(float(np.median(x[m])))
            by.append(float(np.median(y[m])))
    bx_arr = np.asarray(bx, np.float64)
    by_arr = np.asarray(by, np.float64)
    if bx_arr.size < 2 or np.allclose(bx_arr, bx_arr[0]):
        return 0.0, float(np.median(y))
    slopes: list[float] = []
    for i in range(bx_arr.size):
        dx = bx_arr - bx_arr[i]
        dy = by_arr - by_arr[i]
        ok = np.abs(dx) > 1e-9
        if ok.any():
            slopes.append(float(np.median(dy[ok] / dx[ok])))
    b1 = float(np.median(slopes)) if slopes else 0.0
    b0 = float(np.median(y - b1 * x))
    return b1, b0


def prepare_drainage(
    elev: np.ndarray,
    footprint: np.ndarray,
    *,
    params: dict[str, float] | None = None,
) -> DrainageField:
    """Compute the draw-independent H43 grids (`lnacc`, `omega`, `knick`) once from the DEM and footprint."""
    p = dict(H43_PARAMS)
    if params:
        unknown = set(params) - set(H43_PARAMS)
        if unknown:
            raise ValueError(f"unknown H43 parameters: {sorted(unknown)}")
        p.update(params)

    foot = np.asarray(footprint, bool)
    z_in = np.asarray(elev, np.float64)
    if z_in.shape != foot.shape or z_in.ndim != 2:
        raise ValueError("elev and footprint must be 2-D arrays of identical shape")
    n_foot = int(foot.sum())
    if n_foot == 0:
        raise ValueError("empty footprint")

    finite_in_foot = foot & np.isfinite(z_in)
    n_nan_filled = int(n_foot - int(finite_in_foot.sum()))

    filled = fill_dem(z_in, foot, eps=p["pit_eps"])
    acc, basin, outlet_mask = d8_order(filled, foot, return_basins=True)
    interior = binary_erosion(foot, structure=np.ones((3, 3), bool), border_value=0)
    n_interior_trapped = int((outlet_mask & interior).sum())
    outlet_mass = float(acc[outlet_mask].sum())

    slope = smoothed_slope(z_in, foot, sigma_px=p["slope_smooth_sigma_px"])
    omega_raw = stream_power(acc, slope, m=p["stream_power_m"])

    # 1. H43_LNACC: log10(acc) scaled by its 99.9th percentile inside the footprint.
    lnacc_raw = np.where(foot, np.log10(np.maximum(acc, 1.0)), 0.0)
    lnacc_scale = float(np.percentile(lnacc_raw[foot], p["lnacc_scale_pct"]))
    if lnacc_scale <= 0:
        lnacc_scale = 1.0
    lnacc_grid = np.where(foot, np.clip(lnacc_raw / lnacc_scale, 0.0, 1.0), 0.0).astype(np.float32)

    # 2. H43_OMEGA: stream power scaled between p1 and p99 inside the footprint.
    omega_lo = float(np.percentile(omega_raw[foot], p["omega_lo_pct"]))
    omega_hi = float(np.percentile(omega_raw[foot], p["omega_hi_pct"]))
    if omega_hi <= omega_lo:
        omega_hi = omega_lo + 1.0
    omega_grid = np.where(foot, np.clip((omega_raw - omega_lo) / (omega_hi - omega_lo), 0.0, 1.0), 0.0).astype(
        np.float32
    )

    # 3. H43_KNICK: positive log10(slope) residual above the basin S-A envelope on channel cells (acc >= 25).
    chan = foot & (acc >= float(p["min_channel_acc_px"]))
    chan_idx = np.flatnonzero(chan.ravel())
    knick_grid = np.zeros(foot.shape, np.float32)
    n_major_basins = 0
    b1_glob, b0_glob, knick_p95 = 0.0, 0.0, 1.0
    if chan_idx.size > 0:
        la = np.log10(np.maximum(acc.ravel()[chan_idx], 1.0))
        ls = np.log10(np.maximum(slope.ravel()[chan_idx], float(p["slope_floor"])))
        b1_glob, b0_glob = repeated_median_log_fit(la, ls, n_bins=32)
        fitted = b0_glob + b1_glob * la

        b_ids = basin.ravel()[chan_idx]
        s_ord = np.argsort(b_ids, kind="mergesort")
        b_sorted = b_ids[s_ord]
        _, start, count = np.unique(b_sorted, return_index=True, return_counts=True)
        min_b = int(p["min_basin_channel_px"])
        for st, ct in zip(start, count):
            if int(ct) >= min_b:
                n_major_basins += 1
                sub = s_ord[st : st + ct]
                b1_b, b0_b = repeated_median_log_fit(la[sub], ls[sub], n_bins=16)
                fitted[sub] = b0_b + b1_b * la[sub]

        resid = np.maximum(ls - fitted, 0.0)
        pos_resid = resid[resid > 0]
        knick_p95 = float(np.percentile(pos_resid, p["knick_clip_pct"])) if pos_resid.size > 0 else 1.0
        if knick_p95 <= 0:
            knick_p95 = 1.0
        knick_grid.ravel()[chan_idx] = np.clip(resid / knick_p95, 0.0, 1.0).astype(np.float32)

    diag = dict(
        params={k: float(v) for k, v in p.items()},
        n_footprint_px=n_foot,
        n_elev_nan_in_footprint_filled=n_nan_filled,
        n_cells_raised_by_fill=int((filled[foot] > _nearest_fill_2d(z_in, finite_in_foot)[foot]).sum()),
        n_boundary_outlets=int(outlet_mask.sum()),
        n_interior_trapped=n_interior_trapped,
        outlet_mass_sum=outlet_mass,
        mass_conserved=bool(abs(outlet_mass - n_foot) <= 1e-3 and n_interior_trapped == 0),
        max_acc_px=float(acc[foot].max()),
        channel_px_acc25=int(chan_idx.size),
        channel_fraction_acc25=float(chan_idx.size / n_foot),
        n_major_basins=n_major_basins,
        global_log_slope_b1=b1_glob,
        global_concavity_theta=-b1_glob,
        global_log_slope_b0=b0_glob,
        knick_p95_scale=knick_p95,
        lnacc_p999_scale=lnacc_scale,
        omega_p1=omega_lo,
        omega_p99=omega_hi,
    )
    return DrainageField(lnacc_grid=lnacc_grid, omega_grid=omega_grid, knick_grid=knick_grid, diagnostics=diag)


def build_h43_fields(
    drainage: DrainageField,
    *,
    visible: np.ndarray,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    scarp_vec: np.ndarray,
    params: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return ``(fields, diagnostics)``; ``fields`` is ``(5, n_footprint)`` float32 with rows ``H43_NAMES``.

    ``visible`` is the draw's visible catalogue grid; ``footprint`` is the template footprint; ``footprint_idx``
    its flat indices; ``scarp_vec`` the footprint-vector H27 scarp composite in [0, 1]. The hidden holdout labels
    never enter; ``visible`` enters only through the off-catalogue distance mask (``>= 500 m``).
    """
    p = dict(H43_PARAMS)
    if params:
        unknown = set(params) - set(H43_PARAMS)
        if unknown:
            raise ValueError(f"unknown H43 parameters: {sorted(unknown)}")
        p.update(params)

    foot = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool) & foot
    H, W = foot.shape
    if drainage.lnacc_grid.shape != (H, W):
        raise ValueError("drainage grids must match footprint shape")
    fi = np.asarray(footprint_idx, np.int64)
    if fi.size == 0:
        raise ValueError("empty footprint")
    if (fi < 0).any() or (fi >= H * W).any() or not foot.ravel()[fi].all():
        raise ValueError("footprint_idx must contain only valid flat indices inside the footprint")
    scarp = np.asarray(scarp_vec, np.float32)
    if scarp.shape != (fi.size,):
        raise ValueError("scarp_vec must align with footprint_idx")

    dist_cat = distance_transform_edt(~vis) if vis.any() else np.full((H, W), np.inf, np.float64)
    off_mask = (dist_cat >= float(p["off_catalogue_min_px"])) & foot

    scarp_clean = np.clip(np.nan_to_num(scarp, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    lnacc_vec = drainage.lnacc_grid.ravel()[fi]
    omega_vec = drainage.omega_grid.ravel()[fi]
    knick_vec = drainage.knick_grid.ravel()[fi]
    off_front_vec = (drainage.knick_grid * off_mask.astype(np.float32)).ravel()[fi]
    chan_scarp_vec = np.clip(omega_vec * scarp_clean, 0.0, 1.0)

    out = np.zeros((5, fi.size), np.float32)
    out[0] = lnacc_vec
    out[1] = omega_vec
    out[2] = knick_vec
    out[3] = off_front_vec
    out[4] = chan_scarp_vec
    out = np.clip(out, 0.0, 1.0)

    diag = dict(
        visible_pixels=int(vis.sum()),
        off_catalogue_footprint_fraction=float(off_mask.ravel()[fi].mean()),
        nonzero_fraction={n: float((out[i] > 1e-4).mean()) for i, n in enumerate(H43_NAMES)},
        max_value={n: float(out[i].max()) for i, n in enumerate(H43_NAMES)},
        mean_value={n: float(out[i].mean()) for i, n in enumerate(H43_NAMES)},
    )
    diag.update(drainage.diagnostics)
    return out, diag


def degenerate_fields(fields: np.ndarray, *, min_nonzero_fraction: float = 0.002) -> list[str]:
    """Names of H43 columns too sparse to move a boosted model (the H31 failure mode).

    Pre-declared viability guard: ``min_nonzero_fraction`` = 0.2 % of footprint pixels.
    """
    problems: list[str] = []
    f = np.asarray(fields)
    if f.ndim != 2 or f.shape[0] != len(H43_NAMES):
        raise ValueError("fields must be (5, n_pixels)")
    for i, name in enumerate(H43_NAMES):
        frac = float((np.nan_to_num(f[i]) > 1e-4).mean())
        if frac < min_nonzero_fraction:
            problems.append(f"{name}: nonzero on {frac:.5%} of pixels (< {min_nonzero_fraction:.1%})")
    if not np.isfinite(f).all():
        problems.append("non-finite values in the H43 field block")
    if float(np.nanmin(f)) < -1e-6 or float(np.nanmax(f)) > 1.0 + 1e-6:
        problems.append("H43 fields violate [0, 1]")
    return problems
