"""Small, explicit analysis helpers for the pre-registered H27 2² design."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

H27_ARMS = {"BASE": (-1, -1), "T": (1, -1), "S": (-1, 1), "TS": (1, 1)}
H27_HISTORICAL_HOLDOUT_BEST = 0.15200338908786984


def factorial_2x2_effects(responses: Mapping[str, float]) -> dict[str, float]:
    """Return coded 2² main-effect and interaction contrasts (high-minus-low response differences)."""
    if set(responses) != set(H27_ARMS):
        raise ValueError(f"responses must have exactly these arms: {sorted(H27_ARMS)}")
    y00, y10, y01, y11 = (float(responses[k]) for k in ("BASE", "T", "S", "TS"))
    if not np.isfinite([y00, y10, y01, y11]).all():
        raise ValueError("all four design responses must be finite")
    return {
        "T": (y10 + y11 - y00 - y01) / 2.0,
        "S": (y01 + y11 - y00 - y10) / 2.0,
        "T_x_S": (y00 - y10 - y01 + y11) / 2.0,
    }


def h27_promotion_gate(
    ts_fold_means: Sequence[float],
    base_fold_means: Sequence[float],
    hug_delta: float,
    historical_best: float = H27_HISTORICAL_HOLDOUT_BEST,
    min_gain: float = 0.001,
    max_fold_loss: float = 0.01,
    max_hug_increase: float = 0.10,
) -> dict:
    """Apply both the fixed historical comparator and paired holdout gate; no test-set score is inferred."""
    ts = np.asarray(ts_fold_means, dtype=float)
    base = np.asarray(base_fold_means, dtype=float)
    if ts.shape != (4,) or base.shape != (4,) or not np.isfinite(ts).all() or not np.isfinite(base).all():
        raise ValueError("TS and BASE need four finite, equally weighted spatial-fold means")
    d = ts - base
    mean_gain = float(d.mean())
    folds_positive = int((d > 0.0).sum())
    worst_fold = float(d.min())
    candidate_mean = float(ts.mean())
    paired_pass = bool(
        mean_gain > min_gain
        and folds_positive >= 3
        and worst_fold >= -max_fold_loss
        and hug_delta <= max_hug_increase
    )
    historical_pass = bool(candidate_mean > historical_best)
    return {
        "candidate_mean_dti": candidate_mean,
        "historical_best": float(historical_best),
        "historical_comparator_passed": historical_pass,
        "mean_gain_vs_paired_base": mean_gain,
        "folds_positive": folds_positive,
        "worst_fold_gain": worst_fold,
        "hug_share_delta": float(hug_delta),
        "paired_gate_passed": paired_pass,
        "passed": bool(historical_pass and paired_pass),
        "per_fold_gain": [float(v) for v in d],
    }
