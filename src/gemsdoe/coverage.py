"""Metric-native emission: greedy expected-coverage dotting for the distance-weighted Tversky index (DTI).

Why this module exists
----------------------
The official metric (transcribed in :mod:`gemsdoe.metric` from the competition problem page) is

    DTI = TP_w / (TP_w + alpha * FP_w + beta * FN_w),  alpha = 0.2, beta = 0.8,

with ``TP_w = sum_g max_x p(x) k(d(x,g))`` --- a **maximum** over predictions for every ground-truth
pixel. Two consequences drive every design decision here and are stated so they can be checked:

1. Adding a predicted pixel next to one that already covers a truth pixel adds **no** TP credit but
   does add FP mass. Emission is therefore a *covering* problem, not a thickness problem.
2. Differentiating the metric (with ``FN_w = |G| - TP_w``) gives the marginal trade-off

       emit iff  c/f  >  alpha * TP / (alpha * FP + beta * |G|),

   where ``c`` is the TP credit a new pixel would earn and ``f`` its FP mass. With alpha = 0.2 and
   beta = 0.8 the denominator is dominated by ``0.8 |G|``, i.e. the rule is permissive: mostly recall.

The implemented approximation is a **batched residual-greedy cover**: the expected-credit field is the
triangular-kernel convolution of the uncovered habitat prior, each round places dots by descending
marginal credit with a minimum-separation constraint, and the credit those dots captured is subtracted
before the next round. Placement order is deterministic (ties break by raster index inside
:func:`gemsdoe.thinning.score_ordered_dots`).

Nothing here reads labels, the catalogue, or any score. The prior is supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import convolve, maximum_filter

ALPHA = 0.2
BETA = 0.8


def triangular_kernel(radius_px: float = 3.0) -> np.ndarray:
    """Triangular kernel ``max(1 - d/r, 0)`` on an odd integer grid (same support as the metric)."""
    if not np.isfinite(radius_px) or radius_px <= 0:
        raise ValueError("radius_px must be finite and positive")
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return np.maximum(1.0 - np.hypot(yy, xx) / radius_px, 0.0).astype(np.float32)


def marginal_threshold(tp: float, fp: float, n_truth: float, alpha: float = ALPHA, beta: float = BETA) -> float:
    """``alpha*TP / (alpha*FP + beta*|G|)`` --- the credit-to-FP-mass ratio a new pixel must exceed."""
    denom = alpha * max(fp, 0.0) + beta * max(n_truth, 0.0)
    return float("inf") if denom <= 0 else float(alpha * max(tp, 0.0) / denom)


def estimated_dti(tp: float, fp: float, n_truth: float, alpha: float = ALPHA, beta: float = BETA) -> float:
    """Metric value implied by estimated weighted counts (``FN = |G| - TP``)."""
    fn = max(n_truth - tp, 0.0)
    denom = tp + alpha * fp + beta * fn
    return float(tp / denom) if denom > 0 else 0.0


def kernel_cover(mask: np.ndarray, radius_px: float = 3.0) -> np.ndarray:
    """Per-pixel maximum kernel weight over a binary emission (the metric's max-over-predictions)."""
    mask = np.asarray(mask, np.float32)
    if mask.ndim != 2:
        raise ValueError("2-D mask required")
    k = triangular_kernel(radius_px)
    r = (k.shape[0] - 1) // 2
    padded = np.pad(mask, r)
    best = np.zeros_like(mask)
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            weight = float(k[dy + r, dx + r])
            if weight <= 0.0:
                continue
            shifted = padded[r + dy : r + dy + h, r + dx : r + dx + w] * weight
            np.maximum(best, shifted, out=best)
    return best


@dataclass
class CoverageResult:
    """Emission snapshots at requested dot budgets plus the estimator diagnostics used to pick one."""

    budgets: tuple[int, ...]
    emissions: dict[int, np.ndarray]
    levels: list[dict] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


def _stamp_one(cover: np.ndarray, k: np.ndarray, y: int, x: int) -> None:
    """``cover = max(cover, k)`` centred on ``(y, x)`` (clipped at the grid edge)."""
    r = (k.shape[0] - 1) // 2
    h, w = cover.shape
    y0, y1 = max(y - r, 0), min(y + r + 1, h)
    x0, x1 = max(x - r, 0), min(x + r + 1, w)
    ky0, ky1 = y0 - (y - r), k.shape[0] - ((y + r + 1) - y1)
    kx0, kx1 = x0 - (x - r), k.shape[1] - ((x + r + 1) - x1)
    window = cover[y0:y1, x0:x1]
    np.maximum(window, k[ky0:ky1, kx0:kx1], out=window)


def ordered_dots(score: np.ndarray, candidates: np.ndarray, min_dist: float) -> tuple[np.ndarray, np.ndarray]:
    """Greedy Poisson-disk selection by descending ``score``, returned in selection order.

    Same rule as :func:`gemsdoe.thinning.score_ordered_dots` (keep a pixel iff no kept pixel lies within
    ``min_dist``), but the caller also receives the order, which is what budget snapping needs.
    """
    score = np.asarray(score)
    candidates = np.asarray(candidates, bool)
    if score.shape != candidates.shape:
        raise ValueError("aligned grids required")
    ids = np.flatnonzero(candidates & np.isfinite(score) & (score > 0))
    if ids.size == 0 or min_dist <= 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    ids = ids[np.lexsort((ids, -score.ravel()[ids]))]
    r = int(np.ceil(min_dist))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    disc = (yy * yy + xx * xx) < float(min_dist) ** 2
    H, W = score.shape
    blocked = np.zeros((H + 2 * r, W + 2 * r), bool)
    ys: list[int] = []
    xs: list[int] = []
    for i in ids.tolist():
        y, x = divmod(i, W)
        if blocked[y + r, x + r]:
            continue
        ys.append(y)
        xs.append(x)
        blocked[y : y + 2 * r + 1, x : x + 2 * r + 1] |= disc
    return np.asarray(ys, np.int64), np.asarray(xs, np.int64)


def greedy_coverage(
    prior: np.ndarray,
    valid: np.ndarray,
    *,
    budgets: tuple[int, ...] = (),
    radius_px: float = 3.0,
    min_sep_px: float = 2.0,
    round_cap: int = 25_000,
    gain_floor: float = 0.02,
    max_budget: int | None = None,
    preselect: int = 2,
) -> CoverageResult:
    """Batched residual-greedy covering of ``prior`` inside ``valid``.

    ``prior`` is a non-negative per-pixel weight (habitat probability, or a detector's binary lineament
    mask); its total mass is the ``|G|`` proxy. Returns cumulative binary dot masks at each requested
    budget and the estimated ``(TP, FP, DTI)`` curve along the placement order.
    """
    prior = np.asarray(prior, np.float32)
    valid = np.asarray(valid, bool)
    if prior.shape != valid.shape or prior.ndim != 2:
        raise ValueError("prior and valid must be aligned 2-D arrays")
    if min_sep_px <= 0:
        raise ValueError("min_sep_px must be positive")
    want = tuple(sorted(int(b) for b in budgets))
    hard_cap = int(max(max(want) if want else 0, max_budget or 0))
    if hard_cap <= 0:
        raise ValueError("at least one positive budget (or max_budget) is required")

    k = triangular_kernel(radius_px)
    p = np.where(valid & np.isfinite(prior), prior, 0.0).astype(np.float32)
    total_mass = float(p.sum())
    if total_mass <= 0:
        raise ValueError("prior has no mass inside the valid domain")

    cover = np.zeros_like(p)
    resid = p.copy()
    placed = np.zeros_like(p, bool)
    local = np.minimum(convolve(p, k, mode="constant", cval=0.0), 1.0)
    emissions: dict[int, np.ndarray] = {}
    levels: list[dict] = []
    n_placed = 0
    rounds = 0
    next_budget = 0
    while n_placed < hard_cap and rounds < 10_000:
        gain = convolve(resid, k, mode="constant", cval=0.0)
        gmax = float(gain.max())
        if gmax < gain_floor:
            break
        rounds += 1
        candidates = valid & (gain >= gain_floor)
        if preselect > 1:
            candidates &= gain >= maximum_filter(gain, size=preselect)
        ys, xs = ordered_dots(gain, candidates, min_sep_px)
        if ys.size == 0:
            break
        cap = min(ys.size, max(round_cap, hard_cap - n_placed))
        for y, x in zip(ys[:cap].tolist(), xs[:cap].tolist(), strict=True):
            if placed[y, x]:
                continue
            _stamp_one(cover, k, y, x)
            placed[y, x] = True
            n_placed += 1
            while next_budget < len(want) and n_placed == want[next_budget]:
                emissions[want[next_budget]] = placed.copy()
                next_budget += 1
            if n_placed >= hard_cap:
                break
        resid = p * (1.0 - cover)
        tp_hat = float((p * cover).sum())
        fp_hat = float(np.sum(1.0 - local[placed]))
        levels.append(
            dict(
                round=rounds,
                n=n_placed,
                tp_hat=tp_hat,
                fp_hat=fp_hat,
                n_truth_hat=total_mass,
                dti_hat=estimated_dti(tp_hat, fp_hat, total_mass),
                max_gain=gmax,
            )
        )
    while next_budget < len(want):
        emissions[want[next_budget]] = placed.copy()
        next_budget += 1
    return CoverageResult(
        budgets=want,
        emissions=emissions,
        levels=levels,
        diagnostics=dict(
            radius_px=radius_px,
            min_sep_px=min_sep_px,
            gain_floor=gain_floor,
            round_cap=round_cap,
            preselected=preselect,
            prior_mass=total_mass,
            rounds=rounds,
            n_placed=n_placed,
            valid_pixels=int(valid.sum()),
        ),
    )
