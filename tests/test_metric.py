import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems29.metric import dti_binary, dti_exact, kernel_from_distance  # noqa: E402


def brute_dti(pred, truth):
    """Literal transcription of the official formulas with no distance transforms (tiny grids)."""
    H, W = truth.shape
    G = np.argwhere(truth)
    tp = 0.0
    for gy, gx in G:
        best = 0.0
        for y in range(max(0, gy - 3), min(H, gy + 4)):
            for x in range(max(0, gx - 3), min(W, gx + 4)):
                k = kernel_from_distance(np.array([np.hypot(y - gy, x - gx)]))[0]
                best = max(best, pred[y, x] * k)
        tp += best
    fp = 0.0
    for y in range(H):
        for x in range(W):
            if pred[y, x] <= 0:
                continue
            kmax = 0.0
            for gy, gx in G:
                kmax = max(kmax, kernel_from_distance(np.array([np.hypot(y - gy, x - gx)]))[0])
                if kmax == 1.0:
                    break
            fp += pred[y, x] * (1.0 - kmax)
    fn = len(G) - tp
    return tp / (tp + 0.2 * fp + 0.8 * fn + 1e-7)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_exact_matches_bruteforce(seed):
    rng = np.random.default_rng(seed)
    truth = rng.random((24, 26)) < 0.06
    # guarantee a connected-ish component somewhere and non-empty truth
    truth[5:9, 5:15] = True
    pred = rng.random(truth.shape)
    pred = np.where(rng.random(truth.shape) < 0.4, pred, 0.0)
    b = dti_exact(pred, truth)
    assert abs(b["dti"] - brute_dti(pred, truth)) < 1e-9


def test_binary_path_matches_exact_on_binary():
    rng = np.random.default_rng(7)
    truth = rng.random((20, 22)) < 0.08
    pred = (rng.random(truth.shape) < 0.2).astype(np.float32)
    a = dti_binary(pred, truth)["dti"]
    b = dti_exact(pred, truth)["dti"]
    assert abs(a - b) < 1e-6   # float32 pred, different accumulation orders: agreement to ~1e-8


def test_known_masking_zeroes_both_sides():
    truth = np.zeros((12, 12), bool)
    truth[5, 5] = True
    pred = np.zeros((12, 12), np.float32)
    pred[5, 5] = 1.0
    with_known = dti_binary(pred, truth, known=truth.copy())
    assert with_known["n_truth"] == 0 and with_known["FPw"] == 0.0


def test_range_and_shape_guards():
    truth = np.zeros((6, 6), bool)
    bad = np.full((6, 6), 1.5, np.float32)
    with pytest.raises(ValueError):
        dti_binary(bad, truth)
    with pytest.raises(ValueError):
        dti_exact(np.zeros((5, 5), np.float32), truth)


def test_no_truth_returns_zero_not_nan():
    pred = (np.random.default_rng(0).random((8, 8)) < 0.3).astype(np.float32)
    r = dti_binary(pred, np.zeros((8, 8), bool))
    assert r["dti"] == 0.0 and np.isfinite(r["FPw"])
