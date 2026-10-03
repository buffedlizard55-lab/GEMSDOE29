"""Spatially-blocked, component-masked holdout (sparse-truth regime) with multi-draw replicates.

Design follows the owner's sibling harness (buffedlizard55-lab/GEMSDOE24 `src/gems/holdout.py`,
re-used in GEMSDOE27; re-written here with credit): four spatial quadrants of the footprint; in
each quadrant a random 20 % of 8-connected catalogue components is *hidden* and acts as truth;
everything else in the catalogue is *known* (masked from both emission and the metric).

Disclosed limits (same disclosure the siblings made, verified against their docs 2026-10-03):
the hidden pieces are catalogue-internal, so this proxy under-sees far-field new-fault habitat
(GEMSDOE27 measured 100 % of proxy truth at distance 0 from the published catalogue, while 81.4 %
of the live 0.2477 emission's dots sit >=300 m from it). Use paired comparisons and controls only,
and treat a proxy pass as necessary, not sufficient, for a slot.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label as ndi_label

FOLD_NAMES = ["NW", "NE", "SW", "SE"]
HIDE_FRACTION = 0.20


def make_quadrant_folds(footprint: np.ndarray) -> np.ndarray:
    footprint = np.asarray(footprint, bool)
    yy, xx = np.nonzero(footprint)
    y_med, x_med = int(np.median(yy)), int(np.median(xx))
    H, W = footprint.shape
    gy, gx = np.ogrid[:H, :W]
    fold = np.full((H, W), -1, dtype=np.int8)
    fold[(gy < y_med) & (gx < x_med) & footprint] = 0
    fold[(gy < y_med) & (gx >= x_med) & footprint] = 1
    fold[(gy >= y_med) & (gx < x_med) & footprint] = 2
    fold[(gy >= y_med) & (gx >= x_med) & footprint] = 3
    return fold


def hide_components(truth: np.ndarray, frac: float, seed: int) -> np.ndarray:
    comp, n = ndi_label(truth, structure=np.ones((3, 3), int))
    if n == 0 or frac <= 0:
        return np.zeros_like(truth, bool)
    rng = np.random.default_rng(seed)
    keep = rng.choice(np.arange(1, n + 1), size=max(1, int(round(frac * n))), replace=False)
    return np.isin(comp, keep)


@dataclass
class Split:
    fold_id: int
    name: str
    draw: int
    fold_mask: np.ndarray   # full-grid bool, the quadrant
    hidden: np.ndarray     # full-grid bool, hidden truth (inside quadrant)
    known: np.ndarray        # full-grid bool, catalogue pixels that are NOT hidden (everywhere)


def make_split(labels: np.ndarray, fold: np.ndarray, fold_id: int, draw: int) -> Split:
    fm = fold == fold_id
    hidden = hide_components(labels & fm, HIDE_FRACTION, seed=4242 + fold_id + 1000 * draw)
    return Split(fold_id, FOLD_NAMES[fold_id], draw, fm, hidden, labels & ~hidden)
