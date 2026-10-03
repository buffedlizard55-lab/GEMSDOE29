"""Deterministic Poisson-disk dot thinning (+ a persistence-ranked variant) of a binary emission.

The geometric motivation is metric-derived, not a leaderboard result: a solid one-pixel line can
pay more false-positive mass than a spaced line under a 300 m triangular kernel, while redundant
nearby pixels add limited credit. Historical H19-5, d1.5 and d2.8 files are associated with
owner/user-reported score claims (0.1922, 0.2477 and 0.2600); those claims have no organizer receipt
in this repository and are not evidence that thinning caused the differences. See the score-claim
register and knowledge/02_h29_results_2026-10-03.md for the explicit caveats and geometric analysis.

The plain `dot_thin` algorithm and determinism contract follow buffedlizard55-lab/GEMSDOE24
`src/gems/thinning.py` (re-written here; subset, label-free behavior is regression-tested). The
FIFO breadth-first traversal is seeded from the lowest raster index of each 8-connected component,
so runs are byte-identical.

`dot_thin_ranked` keeps the same blocking geometry but chooses the highest-priority candidate first
(deterministic max-heap with index tie-break). The predecessor H26-0 local spatial proxy reported
score-ordered dots at equal spacing beating score-blind ordering (+0.0037 mean paired sparse DTI,
4/4 folds); that proxy result is not official-score evidence. The ranked variant here tests whether
worm persistence changes ordering without changing spacing.
"""

from __future__ import annotations

import heapq
from collections import deque

import numpy as np
from scipy.ndimage import label


def _disc_offsets(min_dist: float, width: int) -> list[int]:
    r = int(np.ceil(min_dist))
    lim = min_dist * min_dist
    return [dy * width + dx for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx < lim]


def _pad(mask: np.ndarray, min_dist: float):
    H, W = mask.shape
    pad = int(np.ceil(min_dist)) + 1
    Wp, Hp = W + 2 * pad, H + 2 * pad
    padded = np.zeros((Hp, Wp), bool)
    padded[pad:pad + H, pad:pad + W] = mask
    return padded, pad, Hp, Wp


def _crop(kept_flat: np.ndarray, pad: int, Hp: int, Wp: int, H: int, W: int) -> np.ndarray:
    out = np.frombuffer(bytes(kept_flat), dtype=np.uint8).reshape(Hp, Wp).astype(bool)
    return out[pad:pad + H, pad:pad + W]


def dot_thin(mask: np.ndarray, min_dist: float) -> np.ndarray:
    """Keep a pixel iff no already-kept pixel is closer than `min_dist` (Euclidean, pixels)."""
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("2-D mask required")
    if min_dist <= 1.0 or not mask.any():
        return mask.copy()
    H, W = mask.shape
    padded, pad, Hp, Wp = _pad(mask, min_dist)
    flat = bytearray(padded.tobytes())
    visited, blocked, kept = bytearray(Hp * Wp), bytearray(Hp * Wp), bytearray(Hp * Wp)
    disc = _disc_offsets(min_dist, Wp)
    nbr = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)
    comp, _ = label(padded, structure=np.ones((3, 3), int))
    fc = comp.ravel()
    order = np.flatnonzero(fc)
    _, first = np.unique(fc[order], return_index=True)
    for seed in order[np.sort(first)].tolist():
        if visited[seed]:
            continue
        visited[seed] = 1
        q = deque((seed,))
        while q:
            c = q.popleft()
            if not blocked[c]:
                kept[c] = 1
                for o in disc:
                    blocked[c + o] = 1
            for o in nbr:
                n = c + o
                if flat[n] and not visited[n]:
                    visited[n] = 1
                    q.append(n)
    return _crop(kept, pad, Hp, Wp, H, W)


def dot_thin_ranked(mask: np.ndarray, min_dist: float, priority: np.ndarray | None = None) -> np.ndarray:
    """Poisson-disk thinning with a global max-priority greedy order.

    Identical blocking geometry and subset guarantee as `dot_thin`; only the ORDER in which
    candidate pixels claim their exclusion disc changes: highest `priority` first (ties resolved
    by raster index). With priority=None this delegates to `dot_thin` exactly (same output bytes).
    H26-0 (GEMSDOE25) measured score-ordered dots at equal spacing beating score-blind ordering
    (+0.0037 mean paired sparse DTI, 4/4 folds); this lets a new field (worm persistence/ridge
    evidence) enter that proven lever without changing the spacing geometry.
    """
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("2-D mask required")
    if min_dist <= 1.0 or not mask.any():
        return mask.copy()
    if priority is None:
        return dot_thin(mask, min_dist)
    priority = np.asarray(priority, np.float64)
    if priority.shape != mask.shape or not np.isfinite(priority[mask]).all():
        raise ValueError("priority must be finite wherever mask is set")
    H, W = mask.shape
    padded, pad, Hp, Wp = _pad(mask, min_dist)
    flat_mask = padded.ravel()
    prio_f = np.full(Hp * Wp, -np.inf)
    prio_f[flat_mask] = priority.ravel()[mask.ravel()]
    blocked = bytearray(Hp * Wp)
    kept = bytearray(Hp * Wp)
    disc = _disc_offsets(min_dist, Wp)
    heap = [(-prio_f[i], int(i)) for i in np.flatnonzero(flat_mask)]
    heapq.heapify(heap)
    while heap:
        _, c = heapq.heappop(heap)
        if blocked[c]:
            continue
        kept[c] = 1
        for o in disc:
            blocked[c + o] = 1
    return _crop(kept, pad, Hp, Wp, H, W)
