"""Strict aggregation for the preregistered 2-screen / confirmation spatial holdout gate."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np


def gate_from_rows(rows: list[dict[str, Any]], *, family: str, arm: str,
                   delta_key: str = "paired_delta", threshold: float = 0.005,
                   min_positive_folds: int = 3, expected_folds: int = 4,
                   screen_draws: tuple[int, int] = (0, 1),
                   confirmation_draws: tuple[int, int] = (2, 3)) -> dict[str, Any]:
    """Summarize one arm and apply the full frozen gate.

    A draw is complete only when it contains exactly ``expected_folds`` finite rows with the
    expected fold IDs ``0..expected_folds-1``. Both screen draws must pass. At least one complete
    confirmation draw must pass; when all confirmation draws are complete and none passes, the
    gate fails. A missing confirmation remains indeterminate unless another complete confirmation
    passes. A failed complete screen cannot be rescued by a later draw.

    ``family`` selects a row key such as ``A`` or ``B``; ``delta_key`` selects paired deltas.
    """
    if expected_folds < 1:
        raise ValueError("expected_folds must be positive")
    if not 0 <= min_positive_folds <= expected_folds:
        raise ValueError("min_positive_folds must be between 0 and expected_folds")
    if not screen_draws or not confirmation_draws:
        raise ValueError("screen_draws and confirmation_draws must be non-empty")
    if len(set(screen_draws)) != len(screen_draws) or len(set(confirmation_draws)) != len(confirmation_draws):
        raise ValueError("draw IDs must be unique within each phase")
    if set(screen_draws) & set(confirmation_draws):
        raise ValueError("screen and confirmation draw IDs must not overlap")

    by_draw: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        if family not in row or arm not in row[family]:
            continue
        metrics = row[family][arm]
        if delta_key not in metrics:
            continue
        by_draw[int(row["draw"])].append((int(row["fold"]), float(metrics[delta_key])))

    expected_fold_ids = list(range(expected_folds))

    def summarize(draw: int) -> dict[str, Any]:
        items = sorted(by_draw.get(draw, []))
        fold_ids = [fold for fold, _ in items]
        unique = len(set(fold_ids)) == len(fold_ids)
        fold_ids_valid = fold_ids == expected_fold_ids
        vals = np.asarray([delta for _, delta in items], dtype=np.float64)
        finite_mask = np.isfinite(vals)
        finite = bool(finite_mask.all())
        complete = unique and fold_ids_valid and len(items) == expected_folds and finite
        mean_delta = float(vals.mean()) if vals.size and finite else None
        positive_folds = int(np.sum(vals[finite_mask] > 0.0))
        return {
            "complete": bool(complete),
            "n_folds": len(items),
            "folds": fold_ids,
            "fold_ids_valid": bool(fold_ids_valid),
            "all_deltas_finite": finite,
            "mean_delta": mean_delta,
            "positive_folds": positive_folds,
            "deltas": [float(x) if np.isfinite(x) else None for x in vals],
            "passed_threshold": bool(complete and mean_delta >= threshold
                                      and positive_folds >= min_positive_folds),
        }

    draws = sorted(set(by_draw) | set(screen_draws) | set(confirmation_draws))
    per_draw = {f"draw{d}": summarize(d) for d in draws}
    screen_complete = all(per_draw[f"draw{d}"]["complete"] for d in screen_draws)
    screen_pass: bool | None = (all(per_draw[f"draw{d}"]["passed_threshold"] for d in screen_draws)
                                if screen_complete else None)
    complete_confirmations = [d for d in confirmation_draws if per_draw[f"draw{d}"]["complete"]]
    confirm_draw = next((f"draw{d}" for d in confirmation_draws
                         if per_draw[f"draw{d}"]["passed_threshold"]), None)

    if screen_complete and screen_pass is False:
        # A failed screen cannot be rescued by confirmation; stopping here saves preregistered
        # compute without turning an unrun confirmation into a result.
        passed: bool | None = False
    elif screen_complete and screen_pass is True:
        if confirm_draw is not None:
            passed = True
        elif len(complete_confirmations) == len(confirmation_draws):
            passed = False
        else:
            passed = None
    else:
        passed = None

    return {
        "family": family,
        "arm": arm,
        "delta_key": delta_key,
        "threshold_mean_delta": float(threshold),
        "min_positive_folds": int(min_positive_folds),
        "expected_folds": int(expected_folds),
        "screen_draws": list(screen_draws),
        "confirmation_draws": list(confirmation_draws),
        "screen_pass": screen_pass,
        "complete_confirmation_draws": [f"draw{d}" for d in complete_confirmations],
        "confirm_draw": confirm_draw,
        "PASS": passed,
        "per_draw": per_draw,
        "interpretation": "catalogue-internal proxy eligibility only; not live/private leaderboard evidence",
    }
