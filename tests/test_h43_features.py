"""Synthetic tests for the H43 drainage-network features (``src/gemsdoe/h43.py``).

Every test builds a surface whose drainage is analytically known, so a routing bug cannot hide behind a
plausible-looking number. The real-band smoke test (pit count, channel fraction) is deliberately left to
the screen runner, which records it as evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemsdoe.h43 import (  # noqa: E402
    build_h43_columns,
    check_strict_descent,
    count_strict_pits,
    d8_receivers,
    fill_and_route,
    fill_depressions,
    flow_accumulation,
    knickpoint_excess,
    robust_loglog_fit,
    stream_power,
)


def tilted_plane(h=12, w=16, dy=0.0, dx=0.75):
    y, x = np.mgrid[0:h, 0:w]
    return -(dy * y + dx * x)


def test_receivers_on_a_plane_are_strictly_descending_and_point_east():
    elev = tilted_plane()
    valid = np.ones_like(elev, bool)
    receiver, drop = d8_receivers(elev, valid)
    rec = receiver.reshape(elev.shape)
    assert check_strict_descent(elev, receiver, valid) == 0.0
    # every cell except the last column drains to its +x neighbour; last column has no lower neighbour
    assert np.array_equal(rec[:, :-1], np.arange(elev.size).reshape(elev.shape)[:, 1:])
    assert (rec[:, -1] == -1).all()
    assert np.allclose(drop.reshape(elev.shape)[:, :-1], 0.75)


def test_accumulation_on_a_plane_is_linear_and_conserves_mass():
    elev = tilted_plane(h=12, w=16)
    valid = np.ones_like(elev, bool)
    r = fill_and_route(elev, valid)
    acc = r["acc"]
    assert np.array_equal(acc[:, 0], np.ones(elev.shape[0], np.int64))
    assert np.array_equal(acc[:, -1], np.full(elev.shape[0], elev.shape[1], np.int64))
    assert acc.sum() == 12 * (np.arange(1, 17).sum())  # each column c holds c+1 cells
    outlets = r["receiver"] < 0
    assert int(acc.ravel()[outlets].sum()) == int(valid.sum())  # mass conservation


def test_v_valley_concentrates_flow_on_the_thalweg():
    h, w, xc = 20, 21, 10.5
    y, x = np.mgrid[0:h, 0:w]
    elev = 2.0 * np.abs(xc - x) - 0.5 * y
    valid = np.ones_like(elev, bool)
    r = fill_and_route(elev, valid)
    acc = r["acc"]
    # the axis is the only place where column-wise maxima may sit (ties are broken deterministically)
    assert set(np.unique(np.argmax(acc, axis=1)).tolist()) <= {10, 11}
    # flow concentrates down-valley: the two axis columns carry nearly all of the mass
    axis_mass = acc[:, 10].sum() + acc[:, 11].sum()
    assert axis_mass > 0.5 * acc.sum()
    assert acc[-1, 10] + acc[-1, 11] > acc[0, 10] + acc[0, 11]
    outlets = r["receiver"] < 0
    assert int(acc.ravel()[outlets].sum()) == int(valid.sum())  # mass conservation


def test_depression_filling_removes_pits_and_never_lowers_the_surface():
    elev = tilted_plane(h=10, w=12)
    elev[5, 5] = elev[5, 5] - 3.0  # a closed pit
    valid = np.ones_like(elev, bool)
    assert count_strict_pits(elev, valid) == 1
    filled = fill_depressions(elev, valid)
    assert count_strict_pits(filled, valid) == 0
    assert (filled[valid] >= elev[valid] - 1e-12).all()
    changed = filled != elev
    assert changed.sum() == 1 and changed[5, 5]
    r = fill_and_route(elev, valid)
    assert r["pits"] == 1 and r["fill_changed"] is True
    outlets = r["receiver"] < 0
    assert int(r["acc"].ravel()[outlets].sum()) == int(valid.sum())  # every cell drains to a boundary outlet


def test_flow_accumulation_requires_a_topological_order_when_given_one():
    elev = tilted_plane(h=6, w=8)
    valid = np.ones_like(elev, bool)
    receiver, _ = d8_receivers(elev, valid)
    order = np.argsort(elev.ravel(), kind="stable")[::-1]  # high to low = topological for this plane
    acc = flow_accumulation(receiver, valid, order=order)
    assert np.array_equal(acc[:, -1], np.full(6, 8, np.int64))


def test_robust_fit_recovers_a_known_concavity():
    rng = np.random.default_rng(0)
    log_a = rng.uniform(1.4, 5.5, 40_000)
    log_s = -1.2 - 0.45 * log_a + rng.normal(0, 0.05, log_a.size)
    fit = robust_loglog_fit(log_a, log_s)
    assert abs(fit["theta"] - 0.45) < 0.02
    assert abs(fit["intercept"] - (-1.2)) < 0.1


def test_knickpoint_excess_is_zero_on_a_perfect_profile_and_positive_on_a_step():
    h = w = 120
    acc = np.zeros((h, w), np.float64)
    acc[:] = np.power(10.0, np.linspace(1.6, 5.0, w))[None, :]
    slope = np.power(10.0, -1.0 - 0.45 * np.log10(acc))
    valid = np.ones((h, w), bool)
    knick, diag = knickpoint_excess(acc, slope, valid)
    assert knick.max() == 0.0  # an exact power-law profile has no knickpoints
    bumped = slope.copy()
    bumped[60, 60] *= 50.0
    knick2, diag2 = knickpoint_excess(acc, bumped, valid)
    assert knick2[60, 60] == 1.0  # the only positive-residual pixel maps to the top of the scale
    assert knick2.sum() - knick2[60, 60] == 0.0  # localised: exactly one pixel has a positive residual
    assert diag2["positive_residual_pixels"] == 1
    assert diag["fit"]["theta"] == diag2["fit"]["theta"]  # the fit is median-based, robust to one outlier
    assert diag2["channel_pixels"] == h * w
    assert np.all(0.0 <= knick2) and np.all(knick2 <= 1.0)


def test_stream_power_is_monotone_in_both_inputs():
    acc = np.array([[10.0, 100.0], [10.0, 100.0]])
    slope = np.array([[0.1, 0.1], [0.2, 0.2]])
    om = stream_power(acc, slope)
    assert om[0, 0] < om[0, 1] and om[0, 0] < om[1, 0] < om[1, 1]


def test_build_h43_columns_is_bounded_deterministic_and_off_support_blind():
    h, w = 80, 90
    y, x = np.mgrid[0:h, 0:w]
    elev = 2.0 * np.abs(45.5 - x) - 0.5 * y  # a V-valley: a real channel network with large catchments
    valid = np.ones((h, w), bool)
    scarp = np.linspace(0.0, 1.0, w)[None, :].repeat(h, axis=0)
    cols, diag = build_h43_columns(elev, valid, scarp, off_mask=None)
    assert set(cols) == {"H43_LNACC", "H43_OMEGA", "H43_KNICK", "H43_OFF_FRONT", "H43_CHANNEL_SCARP"}
    for name, v in cols.items():
        assert v.shape == elev.shape
        assert np.isfinite(v).all(), name
        assert v.min() >= 0.0 and v.max() <= 1.0, name
    assert cols["H43_OFF_FRONT"].max() == 0.0  # never built without an explicit off-catalogue mask
    assert set(diag["nonzero_fraction"]) == set(cols)
    cols2, diag2 = build_h43_columns(elev, valid, scarp, off_mask=None)
    assert all(np.array_equal(cols[k], cols2[k]) for k in cols)
    assert diag["pits"] == diag2["pits"]

    half = np.zeros((h, w), bool)
    half[:, : w // 2] = True
    cols3, _ = build_h43_columns(elev, valid, scarp, off_mask=half)
    assert np.all(cols3["H43_OFF_FRONT"][:, w // 2 :] == 0.0)
    assert np.allclose(cols3["H43_OFF_FRONT"][:, : w // 2], cols3["H43_KNICK"][:, : w // 2])
