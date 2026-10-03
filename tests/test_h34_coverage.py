"""Synthetic checks for the metric-native coverage emission (H34).

These tests use only constructed arrays: no labels, no competition data, no scores.
"""

from __future__ import annotations

import numpy as np

from gemsdoe.coverage import (
    estimated_dti,
    greedy_coverage,
    kernel_cover,
    marginal_threshold,
    triangular_kernel,
)


def test_kernel_matches_metric_support():
    k = triangular_kernel(3.0)
    assert k.shape == (7, 7)
    assert k[3, 3] == 1.0
    assert k[3, 0] == 0.0 and k[0, 3] == 0.0
    # centre-to-edge weight at 1 px is 2/3, exactly the linear kernel
    assert abs(float(k[3, 4]) - (1 - 1 / 3)) < 1e-6


def test_kernel_cover_is_max_over_predictions():
    mask = np.zeros((11, 11), bool)
    mask[5, 5] = True
    cover = kernel_cover(mask, 3.0)
    assert abs(float(cover[5, 5]) - 1.0) < 1e-6
    assert abs(float(cover[5, 6]) - (1 - 1 / 3)) < 1e-6
    assert float(cover[5, 5 + 3]) == 0.0
    # a second, nearer dot cannot reduce coverage of the first
    mask2 = mask.copy()
    mask2[5, 6] = True
    assert np.all(kernel_cover(mask2, 3.0) >= cover - 1e-6)


def test_estimators_match_published_worked_example():
    # Competition page worked example: TP_w 3.00, FP_w 1.89, FN_w 2.00 -> 0.60
    assert abs(estimated_dti(tp=3.0, fp=1.89, n_truth=5.0) - 3.0 / (3.0 + 0.2 * 1.89 + 0.8 * 2.0)) < 1e-9
    tau = marginal_threshold(tp=3.0, fp=1.89, n_truth=5.0)
    assert abs(tau - (0.2 * 3.0) / (0.2 * 1.89 + 0.8 * 5.0)) < 1e-12


def test_greedy_covers_everything_it_needs_to_and_stops():
    prior = np.zeros((40, 40), np.float32)
    prior[5:35, 20] = 1.0  # a line of mass
    valid = np.ones_like(prior, bool)
    res = greedy_coverage(prior, valid, budgets=(10, 30, 100), min_sep_px=2.0, gain_floor=0.05)
    assert res.diagnostics["prior_mass"] == 30.0
    n10, n30, n100 = (int(res.emissions[b].sum()) for b in (10, 30, 100))
    assert n10 <= 10 and n30 <= 30 and n100 <= 100
    assert n10 < n30 <= n100
    # one dot per ~2 px along the line already captures most of the credit; the budget cap is not binding
    cover = kernel_cover(res.emissions[100], 3.0)
    assert float((prior * cover).sum()) >= 0.9 * res.diagnostics["prior_mass"]
    assert res.levels[-1]["tp_hat"] >= 0.9 * res.diagnostics["prior_mass"]
    assert res.levels[-1]["dti_hat"] > 0.5


def test_greedy_is_deterministic():
    rng = np.random.default_rng(3)
    prior = (rng.random((30, 30)) > 0.9).astype(np.float32)
    valid = np.ones_like(prior, bool)
    a = greedy_coverage(prior, valid, budgets=(25,), min_sep_px=2.0)
    b = greedy_coverage(prior, valid, budgets=(25,), min_sep_px=2.0)
    assert np.array_equal(a.emissions[25], b.emissions[25])


def test_greedy_respects_valid_domain():
    prior = np.ones((20, 20), np.float32)
    valid = np.zeros_like(prior, bool)
    valid[5:15, 5:15] = True
    res = greedy_coverage(prior, valid, budgets=(40,), min_sep_px=2.0)
    assert not res.emissions[40][~valid].any()


def test_dti_estimate_is_monotone_in_credit():
    a = estimated_dti(tp=5.0, fp=10.0, n_truth=20.0)
    b = estimated_dti(tp=9.0, fp=10.0, n_truth=20.0)
    assert b > a
    c = estimated_dti(tp=5.0, fp=30.0, n_truth=20.0)
    assert c < a
