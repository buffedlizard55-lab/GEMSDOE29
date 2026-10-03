"""Spatially blocked *hide-and-recover* holdout.

The competition target includes expert-identified faults not present in the existing public catalogue. This
hide-and-recover experiment uses catalogue components only as a spatial-gap proxy; it does not observe or
reconstruct the organizer's hidden expert labels:

1. split the footprint into four contiguous quadrants (median row / column of the footprint);
2. in a draw, hide whole 8-connected fault *components* until ``hide_frac`` of the catalogue's pixels are
   hidden (these play the "new" faults); the remaining catalogue stays **visible** and is excluded from this
   proxy score;
3. a model for test quadrant ``k`` is trained only on the other three quadrants minus a 1.5 km collar and
   never sees a component that touches the test quadrant or its collar;
4. catalogue-geometry features are computed from the *visible* catalogue only.

``hide_frac = 0.20`` is a fixed engineering choice for component hide-and-recover tests; it is not inferred from
an organizer-hidden-label fraction. The simulation is a *catalogue-gap* proxy, not new-fault truth. Its relationship
to the public or private competition scores is unknown, so holdout DTI must never be presented as a competition score.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import binary_dilation, label

from .metric import dti_binary

FOLD_NAMES = ("NW", "NE", "SW", "SE")
COLLAR_PX = 15  # 1.5 km


def quadrant_ids(footprint: np.ndarray) -> np.ndarray:
    """Quadrant id (0..3) per pixel, -1 outside the footprint; split at the footprint's median row/col."""
    footprint = np.asarray(footprint, bool)
    yy, xx = np.nonzero(footprint)
    ym, xm = int(np.median(yy)), int(np.median(xx))
    H, W = footprint.shape
    gy, gx = np.ogrid[:H, :W]
    q = np.full((H, W), -1, np.int8)
    q[(gy < ym) & (gx < xm) & footprint] = 0
    q[(gy < ym) & (gx >= xm) & footprint] = 1
    q[(gy >= ym) & (gx < xm) & footprint] = 2
    q[(gy >= ym) & (gx >= xm) & footprint] = 3
    return q


@dataclass
class Draw:
    """One hide-and-recover realisation for one test quadrant."""

    fold: int
    seed: int
    quadrant: np.ndarray  # bool, test quadrant (inside footprint)
    collar: np.ndarray  # bool, quadrant dilated by COLLAR_PX (includes the quadrant)
    hidden_test: np.ndarray  # new-fault truth, inside the test quadrant only (scored)
    hidden_train: np.ndarray  # pseudo-new faults (positives) in the training region
    visible: np.ndarray  # known catalogue everywhere (masked in scoring, input to catalogue features)
    train_region: np.ndarray  # footprint minus collar
    bbox: tuple  # (slice, slice) bounding box of the quadrant


class Holdout:
    def __init__(self, footprint: np.ndarray, labels: np.ndarray, hide_frac: float = 0.20):
        self.footprint = np.asarray(footprint, bool)
        self.labels = np.asarray(labels, bool) & self.footprint
        self.hide_frac = float(hide_frac)
        self.quad = quadrant_ids(self.footprint)
        self.comp, self.n_comp = label(self.labels, structure=np.ones((3, 3), int))
        self.comp_size = np.bincount(self.comp.ravel(), minlength=self.n_comp + 1)
        self._collar: dict[int, np.ndarray] = {}

    def collar(self, fold: int) -> np.ndarray:
        if fold not in self._collar:
            q = self.quad == fold
            self._collar[fold] = (
                binary_dilation(q, structure=np.ones((3, 3), bool), iterations=COLLAR_PX) & self.footprint
            )
        return self._collar[fold]

    def _pick(self, rng, ids: np.ndarray, target_px: float) -> np.ndarray:
        """Random components (in random order) until their pixel count reaches ``target_px``."""
        if ids.size == 0:
            return ids
        perm = rng.permutation(ids)
        cum = np.cumsum(self.comp_size[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        return perm[: min(k, perm.size)]

    def draw(self, fold: int, seed: int) -> Draw:
        rng = np.random.default_rng(10_000 * (seed + 1) + fold)
        q = self.quad == fold
        collar = self.collar(fold)
        ids = np.arange(1, self.n_comp + 1)
        touch_collar = np.isin(ids, np.unique(self.comp[collar & self.labels]))
        in_test = np.isin(ids, np.unique(self.comp[q & self.labels]))
        test_ids = ids[in_test]
        train_ids = ids[~touch_collar]
        hid_test = self._pick(rng, test_ids, self.hide_frac * float((self.labels & q).sum()))
        hid_train = self._pick(rng, train_ids, self.hide_frac * float(self.comp_size[train_ids].sum()))
        hidden_full = np.isin(self.comp, hid_test)
        hidden_train = np.isin(self.comp, hid_train)
        visible = self.labels & ~hidden_full & ~hidden_train
        rows = np.flatnonzero(q.any(axis=1))
        cols = np.flatnonzero(q.any(axis=0))
        bbox = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
        return Draw(
            fold=fold,
            seed=seed,
            quadrant=q,
            collar=collar,
            hidden_test=hidden_full & q,
            hidden_train=hidden_train & ~collar,
            visible=visible,
            train_region=self.footprint & ~collar,
            bbox=bbox,
        )

    @staticmethod
    def score(draw: Draw, emitted: np.ndarray) -> dict:
        """Exact sparse-regime DTI of a binary emission inside the draw's test quadrant."""
        sl = draw.bbox
        return dti_binary(
            emitted[sl], draw.hidden_test[sl], valid=draw.quadrant[sl], known=draw.visible[sl]
        )

    @staticmethod
    def score_dense(draw: Draw, emitted: np.ndarray, labels: np.ndarray) -> dict:
        """Dense regime: every catalogue pixel in the quadrant is truth, nothing is masked."""
        sl = draw.bbox
        return dti_binary(emitted[sl], labels[sl] & draw.quadrant[sl], valid=draw.quadrant[sl])
