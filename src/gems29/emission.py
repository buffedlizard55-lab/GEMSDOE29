"""Candidate emission arms for the H29 screen and for shipping the final TIF.

Arms (all restricted to a fold quadrant, all minus the known catalogue, all scored against hidden
catalogue components with the catalogue-masking metric semantics disclosed in metric.py):

  A0  control      : dot_thin(parent_solid, 2.8)                       — reproduces the d2.8 recipe
  A1  worm-gated   : dot_thin(parent_solid & jointP >= TAU, 2.8)       — 'zero-continuation' edges distrusted
  A2  worm-ranked  : dot_thin_ranked(parent_solid, 2.8, priority)      — spacing preserved, order informed
       priority = 0.5*jointP + 0.5*ridge_score,  ridge = mean of lidar ex_max, step_max, relief
  B0/B1/B2 heads   : top-K of dense head probability (K = A0 quadrant pixel count), raw / +worm / +thermal

The parent solid is an owner-mirrored H19-5 emission associated with an unverified owner-reported
score claim; it is NOT a re-run of the 19GEMSDOE recipe. This screen tests the emission-side effect
of worming on fixed local bytes, which keeps every comparison same-run and paired. No leaderboard
receipt or score is used by the code.
"""

from __future__ import annotations

import numpy as np

from .worming import TAU_PERSIST  # single source of truth (0.5), pre-registered in knowledge/01


def parent_solid_from_raster(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (arr > 0.5) & footprint


def ridge_score(lidar_stack: dict[str, np.ndarray]) -> np.ndarray:
    r = (lidar_stack["lid_ex_max"] + lidar_stack["lid_step_max"] + lidar_stack["lid_relief"]) / 3.0
    return r


def emit_A(parent: np.ndarray, valid: np.ndarray, quadrant: np.ndarray, known: np.ndarray,
           jointP: np.ndarray | None, lidar: dict[str, np.ndarray] | None,
           arm: str, min_dist: float = 2.8) -> np.ndarray:
    from .thinning import dot_thin, dot_thin_ranked
    base = parent & valid & quadrant & ~known
    if arm == "A0":
        return dot_thin(base, min_dist)
    if arm == "A1":
        # Distrust number: remove ONLY pixels where worming is defined (a level-0 edge exists)
        # and persistence is below TAU ("exists at zero continuation only"). Pixels where the
        # joint statistic is silent are untouched — worming says nothing about them.
        assert jointP is not None
        defined = jointP["defined"] if isinstance(jointP, dict) else None
        P = jointP["P"] if isinstance(jointP, dict) else jointP
        shallow = (defined > 0.5) & (P < TAU_PERSIST)
        return dot_thin(base & ~shallow, min_dist)
    if arm == "A2":
        assert jointP is not None and lidar is not None
        P = jointP["P"] if isinstance(jointP, dict) else jointP
        defined = jointP["defined"] if isinstance(jointP, dict) else np.zeros(P.shape)
        w = np.where(defined > 0.5, np.clip(np.nan_to_num(P), 0.0, 1.0), 0.5)  # neutral elsewhere
        prio = 0.5 * w + 0.5 * ridge_score(lidar)
        return dot_thin_ranked(base, min_dist, prio)
    raise ValueError(arm)


def emit_B(score: np.ndarray, valid: np.ndarray, quadrant: np.ndarray, known: np.ndarray,
           budget: int) -> np.ndarray:
    """Top-K pixels of a dense score field inside the quadrant, excluding known catalogue pixels."""
    s = np.where(valid & quadrant & ~known, score, -np.inf)
    if budget <= 0:
        return np.zeros(valid.shape, bool)
    idx = np.argpartition(s.ravel(), -budget)[-budget:]
    out = np.zeros(s.size, bool)
    out[idx] = True
    keep = out.reshape(s.shape) & (s > -np.inf)
    return keep
