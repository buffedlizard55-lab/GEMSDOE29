"""H43 — drainage-network organization of the 100 m surface (stream power, knickpoint excess).

The physical claim under test (frozen protocol: ``knowledge/29``): in an extending range, the locus of
active faulting is also the locus of the topographic boundary condition — water leaves along the front —
and the *network* statistics of that surface (contributing area and its residual steepness) carry structural
information that no local window of the supplied 100 m bands can reproduce.

Everything in this module is derived from the cached ``det_elev`` band plus the *visible* catalogue only.
Nothing here reads labels, probabilities or truth masks; the single label-dependent column (``H43_OFF_FRONT``)
is built by the caller from the per-draw visible catalogue, exactly as H41's off-catalogue restriction is.

Determinism: every routine is a pure function of its inputs (no RNG, no iteration count, no tolerance that
depends on data order). Ties in the steepest-descent search are broken by a fixed neighbour order.

Honest caveats carried into the docstrings rather than discovered later:

* ``det_elev`` is a *detrended* surface (it spans about −590…+1470 m and its absolute datum is unknown), so
  only relative topography is used. The routing is therefore "down the cached surface", which is a
  topographic proxy, not a surveyed hydrologic network — stated in the preregistration and in the screen
  summary, never upgraded to a claim about real discharge.
* The D8 receiver graph is required to be *strictly* descending in elevation. That makes it acyclic by
  construction, so no depression filling is needed for correctness; ``fill_depressions`` is implemented and
  tested anyway because the frozen plan asked for it, and the screen reports the measured pit count so the
  no-op can be verified rather than assumed (it was 0 strict pits on the real band).
"""

from __future__ import annotations

import heapq

import numpy as np
from scipy.ndimage import gaussian_filter

H43_NAMES = ("H43_LNACC", "H43_OMEGA", "H43_KNICK", "H43_OFF_FRONT", "H43_CHANNEL_SCARP")

NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
NEIGHBOUR_DIST = tuple(float(np.hypot(dy, dx)) for dy, dx in NEIGHBOURS)
CHANNEL_MIN_CELLS = 25  # frozen in knowledge/29 §3.3 (0.25 km^2 at 100 m pixels)
KNICK_BINS = 20
OMEGA_M = 0.5
SLOPE_SIGMA_PX = 1.0


def _shift(a: np.ndarray, dy: int, dx: int, fill: float) -> np.ndarray:
    """Shift ``a`` by (dy, dx) with constant ``fill`` at the borders (never wraps)."""
    out = np.full_like(a, fill)
    h, w = a.shape
    ys = slice(max(dy, 0), h + min(dy, 0))
    yd = slice(max(-dy, 0), h + min(-dy, 0))
    xs = slice(max(dx, 0), w + min(dx, 0))
    xd = slice(max(-dx, 0), w + min(-dx, 0))
    out[yd, xd] = a[ys, xs]
    return out


def d8_receivers(elev: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Steepest-descent receiver of every valid cell.

    Returns ``(receiver, drop)``: flat indices of the downstream neighbour (``-1`` where the cell has no
    strictly lower valid neighbour) and the elevation drop per pixel of that step. A neighbour is only ever
    accepted when it is *strictly* lower, which is what makes the graph acyclic.
    """
    elev = np.asarray(elev, np.float64)
    valid = np.asarray(valid, bool)
    if elev.shape != valid.shape or elev.ndim != 2:
        raise ValueError("elev and valid must be equal-shaped 2-D arrays")
    h, w = elev.shape
    e = np.where(valid, elev, np.inf)
    best_slope = np.zeros((h, w), np.float64)
    best_idx = np.full((h, w), -1, np.int64)
    for (dy, dx), dist in zip(NEIGHBOURS, NEIGHBOUR_DIST):
        n = _shift(e, dy, dx, np.inf)
        drop = e - n
        accept = np.isfinite(n) & (drop > 0.0)
        slope = np.where(accept, drop / dist, 0.0)
        better = slope > best_slope
        if better.any():
            yy, xx = np.nonzero(better)
            best_slope[yy, xx] = slope[yy, xx]
            best_idx[yy, xx] = (yy + dy) * w + (xx + dx)
    receiver = np.where(valid, best_idx, -1).ravel()
    drop = np.where(valid, best_slope * 1.0, 0.0).ravel()
    return receiver, drop


def check_strict_descent(elev: np.ndarray, receiver: np.ndarray, valid: np.ndarray) -> float:
    """Largest non-negative ``elev(receiver) - elev(cell)`` over all receivers (0.0 = strictly descending)."""
    flat = np.asarray(elev, np.float64).ravel()
    ok = receiver >= 0
    if not ok.any():
        return 0.0
    src = np.flatnonzero(ok)
    diff = flat[receiver[src]] - flat[src]
    return float(max(0.0, diff.max())) if diff.size else 0.0


def count_strict_pits(elev: np.ndarray, valid: np.ndarray) -> int:
    """Cells whose 8 neighbours are all higher-or-equal (closed depressions on the supplied surface)."""
    elev = np.asarray(elev, np.float64)
    valid = np.asarray(valid, bool)
    higher = np.ones(elev.shape, bool)
    for dy, dx in NEIGHBOURS:
        n = _shift(elev, dy, dx, np.inf)
        higher &= np.isfinite(n) & (n > elev)
    return int(np.count_nonzero(valid & higher & np.isfinite(elev)))


def fill_depressions(elev: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Priority-flood depression filling (Barnes, Lehman & Mulla 2014) on the valid cells.

    Returns a copy of ``elev`` in which every closed depression is raised to its spill elevation. The
    algorithm is standard and deterministic: a min-heap seeded with the valid boundary cells pops the
    lowest cell, raises each unvisited valid neighbour to at least the popped elevation and pushes it.
    """
    elev = np.asarray(elev, np.float64).copy()
    valid = np.asarray(valid, bool)
    if elev.shape != valid.shape or elev.ndim != 2:
        raise ValueError("elev and valid must be equal-shaped 2-D arrays")
    h, w = elev.shape
    work = np.where(valid, elev, np.nan)
    out = np.full((h, w), np.nan, np.float64)
    visited = np.zeros((h, w), bool)
    heap: list[tuple[float, int, int]] = []
    border = np.zeros((h, w), bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    for y, x in zip(*np.nonzero(valid & border)):
        out[y, x] = work[y, x]
        visited[y, x] = True
        heapq.heappush(heap, (float(work[y, x]), int(y), int(x)))
    while heap:
        level, y, x = heapq.heappop(heap)
        for dy, dx in NEIGHBOURS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and valid[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                out[ny, nx] = max(float(work[ny, nx]), level)
                heapq.heappush(heap, (float(out[ny, nx]), ny, nx))
    if not np.isfinite(out[valid]).all():  # pragma: no cover - defensive: disconnected valid islands
        out[valid & ~np.isfinite(out)] = work[valid & ~np.isfinite(out)]
    return out


def flow_accumulation(receiver: np.ndarray, valid: np.ndarray, *, order: np.ndarray | None = None) -> np.ndarray:
    """Number of valid cells draining through each cell (itself included), in the receiver forest.

    ``order`` must be a decreasing-elevation order of the valid cells (strict descent guarantees a
    topological order); when omitted, cells are processed in descending flat index which is *not* a
    topological order and is only safe for tests with an explicit order.
    """
    grid_shape = np.asarray(valid).shape
    valid = np.asarray(valid, bool).ravel()
    receiver = np.asarray(receiver, np.int64).ravel()
    if receiver.shape != valid.shape:
        raise ValueError("receiver and valid must share a shape")
    if order is None:
        order = np.flatnonzero(valid)[::-1]
    acc = np.zeros(valid.size, np.int64)
    acc[valid] = 1
    acc_l = acc.tolist()
    recv_l = receiver.tolist()
    for i in np.asarray(order).tolist():
        r = recv_l[i]
        if r >= 0:
            acc_l[r] += acc_l[i]
    return np.asarray(acc_l, np.int64).reshape(grid_shape)


def fill_and_route(elev: np.ndarray, valid: np.ndarray) -> dict:
    """Fill depressions if needed, route D8, accumulate. Returns grids plus the measured diagnostics."""
    pits = count_strict_pits(elev, valid)
    filled = elev if pits == 0 else fill_depressions(elev, valid)
    receiver, drop = d8_receivers(filled, valid)
    max_uphill = check_strict_descent(filled, receiver, valid)
    if max_uphill > 0.0:  # pragma: no cover - guarded by construction of d8_receivers
        raise RuntimeError(f"receiver graph is not strictly descending (max uphill step {max_uphill})")
    order = np.argsort(np.where(valid, filled, -np.inf).ravel(), kind="stable")[::-1]
    order = order[valid.ravel()[order]]
    acc = flow_accumulation(receiver, valid, order=order)
    return dict(filled=filled, receiver=receiver, drop=drop, acc=acc, pits=pits,
                fill_changed=bool(pits > 0), max_uphill_step=max_uphill)


def masked_gaussian(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing of a masked field with validity-normalised weights (no edge bleed)."""
    num = gaussian_filter(np.where(valid, np.nan_to_num(field, nan=0.0), 0.0), sigma, mode="nearest")
    den = gaussian_filter(valid.astype(np.float64), sigma, mode="nearest")
    out = np.full(field.shape, np.nan, np.float64)
    ok = den > 1e-9
    out[ok] = num[ok] / den[ok]
    out[~valid] = np.nan
    return out


def slope_magnitude(elev: np.ndarray, valid: np.ndarray, sigma: float = SLOPE_SIGMA_PX) -> np.ndarray:
    """|grad| of the smoothed surface, in metres per 100 m pixel (dimensionless rise/run × 100)."""
    sm = masked_gaussian(elev, valid, sigma)
    filled = np.where(np.isfinite(sm), sm, np.nan)
    gy, gx = np.gradient(np.nan_to_num(filled, nan=0.0))
    s = np.hypot(gy, gx)
    return np.where(valid & np.isfinite(sm), s, np.nan)


def stream_power(acc: np.ndarray, slope: np.ndarray, m: float = OMEGA_M) -> np.ndarray:
    """Ω ∝ A^m · S with A in cells (unit-coefficient proxy, never a discharge claim)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        omega = np.power(acc.astype(np.float64), m) * slope
    return omega


def robust_loglog_fit(log_a: np.ndarray, log_s: np.ndarray, bins: int = KNICK_BINS) -> dict:
    """Binned-median robust fit of ``log10 S`` on ``log10 A`` (deterministic, no RNG, no scipy optimiser).

    Returns ``(intercept, slope, bin_centres)``: ``slope`` is the concave-profile exponent θ with the sign
    convention ``log10 S ≈ intercept − θ · log10 A``.
    """
    log_a = np.asarray(log_a, np.float64)
    log_s = np.asarray(log_s, np.float64)
    ok = np.isfinite(log_a) & np.isfinite(log_s)
    log_a, log_s = log_a[ok], log_s[ok]
    if log_a.size < 4 * bins:
        raise ValueError(f"too few finite channel pixels ({log_a.size}) for a {bins}-bin robust fit")
    edges = np.quantile(log_a, np.linspace(0.0, 1.0, bins + 1))
    edges = np.unique(edges)
    if edges.size < 4:
        raise ValueError("channel log-area distribution is too degenerate for a robust fit")
    centres, medians = [], []
    idx = np.clip(np.searchsorted(edges, log_a, side="right") - 1, 0, edges.size - 2)
    for b in range(edges.size - 1):
        sel = idx == b
        if np.count_nonzero(sel) >= 25:
            centres.append(float(np.median(log_a[sel])))
            medians.append(float(np.median(log_s[sel])))
    centres = np.asarray(centres)
    medians = np.asarray(medians)
    if centres.size < 3:
        raise ValueError("not enough populated log-area bins for a robust fit")
    slope, intercept = np.polyfit(centres, medians, 1)
    return dict(intercept=float(intercept), slope=float(slope), theta=float(-slope),
                bin_centres=centres.tolist(), bin_medians=medians.tolist(),
                n_channel_pixels=int(log_a.size))


def knickpoint_excess(acc: np.ndarray, slope: np.ndarray, valid: np.ndarray,
                      min_cells: int = CHANNEL_MIN_CELLS) -> tuple[np.ndarray, dict]:
    """Positive residual steepness over the fitted concave profile, clipped at its 95th percentile.

    Channel pixels are ``acc >= min_cells``; the fit is a binned-median log-log fit (see
    :func:`robust_loglog_fit`). The residual is ``log10 S − (intercept − θ log10 A)``, kept only where it is
    positive and normalised by the 95th percentile of the *positive* residuals, so the column is in [0, 1]
    by construction and a spatially sparse knickpoint field still maps its strongest positive residual to
    1.0 instead of collapsing to zero (a plain q95 over all channel pixels would be 0.0 whenever fewer than
    five per cent of channel pixels have a positive residual).
    """
    acc = np.asarray(acc, np.float64)
    slope = np.asarray(slope, np.float64)
    valid = np.asarray(valid, bool)
    channel = valid & (acc >= min_cells) & np.isfinite(slope) & (slope > 0)
    log_a = np.where(channel, np.log10(np.maximum(acc, 1.0)), np.nan)
    log_s = np.where(channel, np.log10(np.maximum(slope, 1e-12)), np.nan)
    fit = robust_loglog_fit(log_a[channel], log_s[channel])
    resid = log_s - (fit["intercept"] + fit["slope"] * log_a)
    pos = np.where(channel & np.isfinite(resid), np.maximum(resid, 0.0), 0.0)
    positive = pos[channel & (pos > 0.0)]
    q95 = float(np.quantile(positive, 0.95)) if positive.size else 0.0
    diag = dict(fit=fit, q95=float(q95), channel_pixels=int(channel.sum()),
                channel_fraction_of_footprint=float(channel.sum() / max(int(valid.sum()), 1)),
                positive_residual_pixels=int(positive.size),
                positive_residual_fraction_of_channels=float(positive.size / max(int(channel.sum()), 1)),
                median_pos_residual=float(np.median(pos[channel])) if np.any(channel) else 0.0)
    if q95 <= 0:
        return np.zeros(acc.shape, np.float64), diag
    return np.clip(pos / q95, 0.0, 1.0), diag


def scale_unit(v: np.ndarray, valid: np.ndarray, *, log: bool = False, q: float = 0.999) -> tuple[np.ndarray, float]:
    """Percentile scaling of a positive field into [0, 1] (log10 first when ``log``)."""
    x = np.asarray(v, np.float64)
    x = np.log10(np.maximum(x, 1.0)) if log else x
    ref = x[valid & np.isfinite(x)]
    if ref.size == 0:
        return np.zeros(x.shape, np.float64), 0.0
    hi = float(np.quantile(ref, q))
    if hi <= 0:
        return np.zeros(x.shape, np.float64), hi
    return np.clip(np.where(np.isfinite(x), x, 0.0) / hi, 0.0, 1.0), hi


def build_h43_columns(elev: np.ndarray, valid: np.ndarray, scarp: np.ndarray,
                      off_mask: np.ndarray | None = None) -> tuple[dict, dict]:
    """The five frozen H43 columns plus their diagnostics.

    ``scarp`` is ``ctx.h27_scarp`` (grid-shaped) and ``off_mask`` the per-draw off-catalogue mask
    (visible catalogue only). When ``off_mask`` is None the off-catalogue column is built entirely
    off-support (all zeros) so callers cannot accidentally leak: it must be supplied explicitly.
    """
    rout = fill_and_route(elev, valid)
    acc = rout["acc"]
    slope = slope_magnitude(rout["filled"], valid)
    omega = stream_power(acc, slope)
    knick, knick_diag = knickpoint_excess(acc, slope, valid)
    lnacc, lnacc_hi = scale_unit(acc, valid, log=True)
    omega_scaled, omega_hi = scale_unit(omega, valid & (acc >= CHANNEL_MIN_CELLS))
    off = np.zeros_like(knick) if off_mask is None else np.where(np.asarray(off_mask, bool), knick, 0.0)
    scarp = np.nan_to_num(np.asarray(scarp, np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    channel_scarp = omega_scaled * np.clip(scarp, 0.0, 1.0)
    columns = {
        "H43_LNACC": np.where(valid, lnacc, 0.0),
        "H43_OMEGA": np.where(valid, omega_scaled, 0.0),
        "H43_KNICK": np.where(valid, knick, 0.0),
        "H43_OFF_FRONT": np.where(valid, off, 0.0),
        "H43_CHANNEL_SCARP": np.where(valid, channel_scarp, 0.0),
    }
    diag = dict(pits=rout["pits"], fill_changed=rout["fill_changed"],
                max_uphill_step=rout["max_uphill_step"],
                slope_px_median=float(np.nanmedian(slope)),
                acc_p99_9=float(np.quantile(acc[valid], 0.999)),
                acc_max=float(acc[valid].max()) if np.any(valid) else 0.0,
                lnacc_ref=float(lnacc_hi), omega_ref=float(omega_hi),
                knick=knick_diag,
                nonzero_fraction={k: float(np.count_nonzero(v[valid])) / max(int(valid.sum()), 1)
                                  for k, v in columns.items()})
    return columns, diag
