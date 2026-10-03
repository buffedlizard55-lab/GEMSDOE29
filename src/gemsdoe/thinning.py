"""Emission geometry: Hessian ridge NMS, positive top-K selection and deterministic dot thinning.

``dot_thin`` keeps a *geodesic Poisson-disk subset* of a binary emission: nothing is added, no label or
score is read, and the traversal is fully deterministic (BFS from the lowest raster index of every
8-connected component). The algorithm reproduces the transform used for the group's 0.2477 submission
(verified pixel-for-pixel in ``tests/test_group_reproduction.py`` when the sibling rasters are present).
"""

from __future__ import annotations

from collections import deque

import numpy as np
from scipy.ndimage import binary_erosion, convolve, gaussian_filter, label


def ridge_nms(score: np.ndarray, valid: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """1-pixel across-strike non-maximum suppression of a score surface (Hessian orientation).

    Keeps pixels that are a local maximum across the direction of strongest negative curvature, with
    negative curvature, positive score and full Gaussian support inside ``valid``.
    """
    score = np.asarray(score, np.float32)
    valid = np.asarray(valid, bool) & np.isfinite(score)
    if score.ndim != 2 or min(score.shape) < 4 or sigma < 0:
        raise ValueError("2-D grid (>=4 px per side) and non-negative sigma required")
    halo = int(np.ceil(4 * sigma)) + 3
    supported = binary_erosion(valid, structure=np.ones((3, 3), bool), iterations=halo, border_value=0)
    s = np.where(valid, score, 0).astype(np.float32)
    ss = gaussian_filter(s, sigma) if sigma > 0 else s
    gy, gx = np.gradient(ss)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    hxy = 0.5 * (hxy + hyx)
    del gy, gx, hyx
    tmp = np.sqrt(((hxx - hyy) * 0.5) ** 2 + hxy**2)
    lam = 0.5 * (hxx + hyy) - tmp  # most negative eigenvalue
    vx, vy = hxy, lam - hxx
    small = (np.abs(vx) + np.abs(vy)) < 1e-12
    vx = np.where(small, 1.0, vx)
    vy = np.where(small, 0.0, vy)
    ang = np.mod(np.degrees(np.arctan2(vy, vx)), 180.0)
    del hxx, hyy, hxy, tmp, vx, vy
    q = (np.round(ang / 45.0).astype(np.int8)) % 4
    concave = lam < -1e-7
    del ang, lam
    pad = np.pad(ss, 1, mode="edge")
    h, w = ss.shape
    c = pad[1:-1, 1:-1]
    offs = {0: (0, 1), 1: (1, 1), 2: (1, 0), 3: (1, -1)}
    keep = np.zeros((h, w), bool)
    for k, (dy, dx) in offs.items():
        a = pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        b = pad[1 - dy : 1 - dy + h, 1 - dx : 1 - dx + w]
        keep |= (q == k) & (c >= a) & (c >= b) & ((c > a) | (c > b))
    return keep & concave & supported & (s > 0)


def select_top_positive(score: np.ndarray, eligible: np.ndarray, k: int) -> np.ndarray:
    """Stable top-k among eligible pixels with strictly positive finite score (never pads with zeros)."""
    score = np.asarray(score)
    eligible = np.asarray(eligible, bool)
    if score.shape != eligible.shape or k < 0:
        raise ValueError("aligned grids and a non-negative budget are required")
    ids = np.flatnonzero(eligible & np.isfinite(score) & (score > 0))
    out = np.zeros(eligible.shape, bool)
    if k and ids.size:
        order = np.lexsort((ids, -score.ravel()[ids]))
        out.ravel()[ids[order[: min(k, ids.size)]]] = True
    return out


def _disc(min_dist: float, width: int) -> list[int]:
    r = int(np.ceil(min_dist))
    lim = min_dist * min_dist
    return [dy * width + dx for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dy * dy + dx * dx < lim]


def dot_thin(mask: np.ndarray, min_dist: float) -> np.ndarray:
    """Deterministic geodesic Poisson-disk subset of ``mask`` (a pixel is kept if no kept pixel is closer
    than ``min_dist``). ``min_dist <= 1`` returns the mask unchanged."""
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("2-D mask required")
    if min_dist <= 1.0 or not mask.any():
        return mask.copy()
    H, W = mask.shape
    pad = int(np.ceil(min_dist)) + 1
    Wp, Hp = W + 2 * pad, H + 2 * pad
    padded = np.zeros((Hp, Wp), bool)
    padded[pad : pad + H, pad : pad + W] = mask
    flat = bytearray(padded.tobytes())
    visited, blocked, kept = bytearray(Hp * Wp), bytearray(Hp * Wp), bytearray(Hp * Wp)
    disc = _disc(min_dist, Wp)
    nbr = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)
    comp, _ = label(padded, structure=np.ones((3, 3), int))
    fc = comp.ravel()
    order = np.flatnonzero(fc)
    _, first = np.unique(fc[order], return_index=True)
    for seed in order[np.sort(first)].tolist():
        if visited[seed]:
            continue
        visited[seed] = 1
        queue = deque((seed,))
        while queue:
            q = queue.popleft()
            if not blocked[q]:
                kept[q] = 1
                for o in disc:
                    blocked[q + o] = 1
            for o in nbr:
                nb = q + o
                if flat[nb] and not visited[nb]:
                    visited[nb] = 1
                    queue.append(nb)
    out = np.frombuffer(bytes(kept), dtype=np.uint8).reshape(Hp, Wp).astype(bool)
    return out[pad : pad + H, pad : pad + W]


def neighbour_profile(mask: np.ndarray) -> dict:
    """How 'solid' an emission is (share of pixels with 0/1/2/3+ 8-neighbours, component size)."""
    mask = np.asarray(mask, bool)
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    nb = convolve(mask.astype(np.int16), k, mode="constant")[mask]
    _, n = label(mask, structure=np.ones((3, 3), int))
    npx = int(mask.sum())
    return dict(
        pixels=npx,
        isolated=float(np.mean(nb == 0)) if npx else 0.0,
        one_neighbour=float(np.mean(nb == 1)) if npx else 0.0,
        two_neighbours=float(np.mean(nb == 2)) if npx else 0.0,
        three_plus=float(np.mean(nb >= 3)) if npx else 0.0,
        components=int(n),
        mean_component_pixels=float(npx / n) if n else 0.0,
    )


def score_ordered_dots(score: np.ndarray, candidates: np.ndarray, min_dist: float, max_keep: int | None = None) -> np.ndarray:
    """Score-aware Poisson-disk dotting (H26-0): visit candidates by descending score and keep a pixel only if
    no already-kept pixel lies within ``min_dist`` (Euclidean, px). Deterministic (ties broken by raster index).

    Unlike :func:`dot_thin` (score-blind, anchored at each component's first raster pixel) the highest-scoring
    pixel of every neighbourhood survives. ``max_keep`` truncates to the best ``max_keep`` kept pixels.
    """
    candidates = np.asarray(candidates, bool)
    score = np.asarray(score)
    if min_dist <= 1.0:
        out = candidates.copy()
    else:
        H, W = candidates.shape
        ids = np.flatnonzero(candidates.ravel())
        order = np.lexsort((ids, -np.nan_to_num(score.ravel()[ids], nan=0.0)))
        ids = ids[order]
        r = int(np.ceil(min_dist))
        yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
        disc = (yy * yy + xx * xx) < min_dist * min_dist
        blocked = np.zeros((H + 2 * r, W + 2 * r), bool)
        out = np.zeros((H, W), bool)
        for i in ids.tolist():
            y, x = divmod(i, W)
            if blocked[y + r, x + r]:
                continue
            out[y, x] = True
            blocked[y : y + 2 * r + 1, x : x + 2 * r + 1] |= disc
    if max_keep is not None and out.sum() > max_keep:
        ids = np.flatnonzero(out.ravel())
        keep = ids[np.lexsort((ids, -np.nan_to_num(score.ravel()[ids], nan=0.0)))[:max_keep]]
        out = np.zeros_like(out)
        out.ravel()[keep] = True
    return out
