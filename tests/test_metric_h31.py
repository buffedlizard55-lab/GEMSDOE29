import numpy as np
import pytest

from gemsdoe.metric import (
    dti_binary,
    dti_bruteforce,
    dti_exact,
    kernel,
    marginal_inclusion_ratio,
)


def test_kernel_matches_official_definition():
    assert kernel(0) == 1.0
    assert kernel(3) == 0.0 and kernel(4) == 0.0
    assert np.isclose(kernel(1.5), 0.5)


def test_exact_equals_bruteforce_on_random_soft_grids():
    rng = np.random.default_rng(0)
    for _ in range(25):
        H, W = 14, 15
        truth = rng.random((H, W)) < 0.07
        pred = np.where(rng.random((H, W)) < 0.25, rng.random((H, W)), 0.0)
        a, b = dti_exact(pred, truth), dti_bruteforce(pred, truth)
        for k in ("tp", "fp", "fn", "dti"):
            assert np.isclose(a[k], b[k], atol=1e-9), (k, a[k], b[k])


def test_binary_fast_equals_exact():
    rng = np.random.default_rng(1)
    for _ in range(25):
        truth = rng.random((30, 31)) < 0.05
        pred = rng.random((30, 31)) < 0.1
        a, b = dti_binary(pred, truth), dti_exact(pred.astype(float), truth)
        for k in ("tp", "fp", "fn", "dti"):
            assert np.isclose(a[k], b[k], atol=1e-9)


def test_identity_tp_plus_fn_equals_truth_count_and_closed_form():
    rng = np.random.default_rng(2)
    truth = rng.random((40, 40)) < 0.04
    pred = rng.random((40, 40)) < 0.08
    r = dti_binary(pred, truth)
    assert np.isclose(r["tp"] + r["fn"], r["n_truth"])
    closed = r["tp"] / (0.2 * (r["tp"] + r["fp"]) + 0.8 * r["n_truth"])
    assert np.isclose(r["dti"], closed, atol=1e-6)


def test_hand_computed_offset_lines():
    # truth: a 20-px vertical line; prediction: the same line shifted by d columns
    truth = np.zeros((30, 30), bool)
    truth[5:25, 10] = True
    for d, expected in [(0, 1.0), (1, 2 / 3), (2, 1 / 3), (3, 0.0)]:
        pred = np.zeros_like(truth)
        pred[5:25, 10 + d] = True
        got = dti_binary(pred, truth)["dti"]
        # offset d: credit (1-d/3) per truth px and false-positive weight d/3 per predicted px
        c = max(1 - d / 3, 0)
        f = min(d / 3, 1.0)
        closed = c / (c + 0.2 * f + 0.8 * (1 - c))
        assert np.isclose(closed, expected, atol=1e-12)  # hand value
        assert np.isclose(got, expected, atol=1e-6)  # implementation


def test_known_pixels_are_masked_and_do_not_matter():
    truth = np.zeros((20, 20), bool)
    truth[10, 5:15] = True
    known = np.zeros_like(truth)
    known[3, :] = True
    base = np.zeros_like(truth)
    base[10, 5:15] = True
    with_known = base.copy()
    with_known[3, :] = True  # emission on masked known pixels
    a = dti_binary(base, truth, known=known)["dti"]
    b = dti_binary(with_known, truth, known=known)["dti"]
    assert a == b


def test_outside_footprint_is_neutral():
    truth = np.zeros((20, 20), bool)
    truth[10, 5:15] = True
    valid = np.ones_like(truth)
    valid[:, :2] = False
    pred = np.zeros_like(truth)
    pred[10, 5:15] = True
    pred[0, 0] = True  # outside footprint
    assert dti_binary(pred, truth, valid=valid)["dti"] == pytest.approx(1.0, abs=1e-6)


def test_invalid_prediction_range_is_rejected():
    truth = np.zeros((5, 5), bool)
    truth[2, 2] = True
    bad = np.zeros((5, 5))
    bad[2, 2] = 1.5
    with pytest.raises(ValueError):
        dti_exact(bad, truth)
    nan = np.zeros((5, 5))
    nan[1, 1] = np.nan
    with pytest.raises(ValueError):
        dti_exact(nan, truth)


def test_marginal_inclusion_ratio_is_the_break_even_of_adding_a_pixel():
    # Verify numerically: adding a pixel with credit dc and fp mass f changes DTI sign at the ratio.
    tp, fp, n = 40.0, 300.0, 100.0
    d = tp / (0.2 * (tp + fp) + 0.8 * n)
    r = marginal_inclusion_ratio(d)
    f = 1.0
    for dc, sign in [(r * f * 1.05, 1), (r * f * 0.95, -1)]:
        d2 = (tp + dc) / (0.2 * (tp + dc + fp + f) + 0.8 * n)
        assert np.sign(d2 - d) == sign
