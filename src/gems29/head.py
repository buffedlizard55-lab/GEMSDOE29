"""Head fitting for the holdout screen: HistGradientBoosting on raw vs raw+worm feature sets.

Deliberately the smallest defensible head (2 CPU cores, no GPU in this sandbox — GEMSDOE25
recorded the same limitation). Negatives are subsampled at a fixed ratio; ranking quality (not
calibration) is what the emission arms consume, so no probability corrections are attempted.
"""

from __future__ import annotations

import numpy as np


def fit_head(X: np.ndarray, y: np.ndarray, seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier
    clf = HistGradientBoostingClassifier(
        max_iter=150, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=64,
        l2_regularization=1.0, early_stopping=False, random_state=seed)
    clf.fit(X, y)
    return clf


def predict_dense(clf, feats: dict[str, np.ndarray], names: list[str], shape: tuple[int, int],
                  out: np.ndarray, chunk: int = 400_000) -> None:
    """Fill `out` (float32 2-D) with clf.predict_proba[:,1] over the full grid, in chunks."""
    n = out.shape[0] * out.shape[1]
    flat = out.reshape(-1)
    cols = [feats[nm].reshape(-1) for nm in names]
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        X = np.stack([c[s:e] for c in cols], axis=1).astype(np.float32)
        flat[s:e] = clf.predict_proba(X)[:, 1]


def subsample_rows(sel_mask: np.ndarray, y: np.ndarray, rng: np.random.Generator,
                   neg_ratio: int = 8, max_pos: int = 400_000):
    """Return (pos_idx, neg_idx) flat indices into sel_mask rows: all positives (capped), ratio*neg."""
    pos = np.nonzero(sel_mask & (y > 0))[0]
    neg = np.nonzero(sel_mask & (y == 0))[0]
    if pos.size > max_pos:
        pos = rng.choice(pos, size=max_pos, replace=False)
    n_neg = min(neg.size, max(pos.size * neg_ratio, 10_000))
    neg = rng.choice(neg, size=n_neg, replace=False)
    return pos, neg
