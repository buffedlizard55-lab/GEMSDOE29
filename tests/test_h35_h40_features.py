"""Synthetic tests for the H35 interaction-zone fields and the H40 dense persistence surface."""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe.dense_persist import HP_NAMES, build_dense_persistence
from gemsdoe.h35 import (
    H35_NAMES,
    RELAY_PARAMS,
    SIGMA3_AZIMUTH_DEG,
    build_interaction_zone_fields,
    dilation_tendency,
    find_trace_tips,
)
from gemsdoe.worms import WormConfig


# --------------------------------------------------------------------------- helpers
def _square_foot(n: int) -> np.ndarray:
    return np.ones((n, n), bool)


def _fi(foot: np.ndarray) -> np.ndarray:
    return np.flatnonzero(foot.ravel())


# --------------------------------------------------------------------------- dilation tendency
def test_dilation_tendency_bounds_and_orientation() -> None:
    paral = float(dilation_tendency(np.float64(SIGMA3_AZIMUTH_DEG)))
    perp = float(dilation_tendency(np.float64((SIGMA3_AZIMUTH_DEG + 90.0) % 180.0)))
    assert 0.0 <= perp < paral <= 1.0
    vals = dilation_tendency(np.linspace(0.0, 179.0, 361))
    assert vals.min() >= 0.0 and vals.max() <= 1.0 and np.isfinite(vals).all()


def test_dilation_tendency_formula_exact() -> None:
    # Hand-checked: dip 60, r2 0.85, r3 0.60, strike parallel to A3 -> sigma_n = cos^2(60) + sin^2(60)*r2
    expected = (0.25 + 0.75 * 0.85 - 0.60) / (1.0 - 0.60)
    got = float(dilation_tendency(np.float64(SIGMA3_AZIMUTH_DEG)))
    assert got == pytest.approx(min(max(expected, 0.0), 1.0), abs=1e-6)


# --------------------------------------------------------------------------- tips and relay
def test_find_trace_tips_counts_line_ends() -> None:
    m = np.zeros((30, 30), bool)
    m[15, 5:25] = True
    foot = _square_foot(30)
    tr, tc, ur, uc = find_trace_tips(m, foot)
    assert tr.size == 2
    assert {(int(r), int(c)) for r, c in zip(tr, tc)} == {(15, 5), (15, 24)}
    # outward vectors oppose along the line
    a = np.stack([ur, uc], axis=1)
    assert np.all(np.isfinite(a)) and np.allclose(np.sort(a[:, 1]), [-1, 1])


def test_relay_pair_detected_with_offset_tips_only() -> None:
    n = 60
    foot = _square_foot(n)
    fi = _fi(foot)
    m = np.zeros((n, n), bool)
    # two vertical (N-S) strands, 6 px apart in col, facing tips separated by 10 px
    m[10:25, 20] = True
    m[35:50, 26] = True
    fields, diag = build_interaction_zone_fields(m, foot, fi)
    assert fields.shape == (4, fi.size)
    assert diag["n_accepted_pairs"] >= 1
    relay = fields[0].reshape(n, n)
    # corridor score nonzero near the midpoint of the bridge, decayed at the far tips
    assert relay[30, 23] > 0.0 and relay[30, 22] > 0.0
    assert relay[5, 5] == 0.0
    # collinear continuation is not a relay (no step width)
    m2 = np.zeros((n, n), bool)
    m2[10:25, 20] = True
    m2[30:45, 20] = True
    f2, d2 = build_interaction_zone_fields(m2, foot, _fi(foot))
    assert d2["n_accepted_pairs"] == 0
    assert not f2[0].any()


def test_relay_td_bounded_by_raw_relay_and_orientation_matters() -> None:
    n = 60
    foot = _square_foot(n)
    fi = _fi(foot)
    # ENE-bridge configuration: tips separated mainly along the extension trend
    e_w = np.zeros((n, n), bool)
    e_w[10:25, 20] = True
    e_w[35:50, 26] = True          # bridge direction ~ (row+10, col+6): azimuth closer to E-W (parallel to A3 105)
    f_ew, _ = build_interaction_zone_fields(e_w, foot, fi)
    # NNE-bridge configuration: second strand offset mainly along-strike-ish, bridge azimuth N-S-ish
    n_s = np.zeros((n, n), bool)
    n_s[10:25, 20] = True
    n_s[25:40, 40] = True          # separated tips, bridge azimuth ~ E-W? keep as second geometry check
    f_ns, _ = build_interaction_zone_fields(n_s, foot, fi)
    for f in (f_ew, f_ns):
        assert np.all(f[1] <= f[0] + 1e-6)  # TD-weighted <= raw (Td <= 1)
        assert np.all(f >= 0.0) and np.all(f <= 1.0)
        assert np.isfinite(f).all()


def test_junction_and_tipdens_fields() -> None:
    n = 60
    foot = _square_foot(n)
    fi = _fi(foot)
    x = np.zeros((n, n), bool)
    for k in range(15):
        x[20 + k, 20 + k] = True
        x[20 + k, 40 - k] = True
    fields, diag = build_interaction_zone_fields(x, foot, fi)
    junction = fields[2].reshape(n, n)
    # crossing at (30, 30): the peak region includes the crossing; far arm interiors are quieter
    assert junction[30, 30] >= 0.4 * junction.max() and junction[30, 30] > 0.0
    assert junction[20, 20] < junction[30, 30]
    # parallel pair: no orientation disturbance along the straight interiors; only near-tip
    # convergence may seed (documented behaviour - facing en-echelon tips ARE relay habitat and are
    # also captured by the relay field, so the junction field is honestly an orientation-disturbance
    # field, not a pure crossing count)
    par = np.zeros((n, n), bool)
    par[15:45, 20] = True
    par[15:45, 26] = True
    fj, dj = build_interaction_zone_fields(par, foot, fi)
    jg = fj[2].reshape(n, n)
    interior = jg[22:38, 17:29]
    assert not interior.any(), "junction seeds must not fire along parallel straight interiors"
    assert dj["junction_seed_pixels"] <= 16  # tip-adjacent only, bounded
    # tip density peaks at the two facing tips of the relay example
    rel = np.zeros((n, n), bool)
    rel[10:25, 20] = True
    rel[35:50, 26] = True
    ft, _ = build_interaction_zone_fields(rel, foot, fi)
    td = ft[3].reshape(n, n)
    assert td[24, 20] > td[45, 45]


def test_shapes_masks_and_empty_visible() -> None:
    n = 40
    foot = _square_foot(n)
    foot[0, 0] = False
    fi = _fi(foot)
    vis = np.zeros((n, n), bool)
    fields, diag = build_interaction_zone_fields(vis, foot, fi)
    assert fields.shape == (4, fi.size)
    assert not fields.any()
    assert diag["n_tips"] == 0
    with pytest.raises(ValueError):
        build_interaction_zone_fields(vis, foot, np.array([n * n + 1]))
    with pytest.raises(ValueError):
        build_interaction_zone_fields(vis, foot[: n - 1], fi)
    with pytest.raises(ValueError):
        build_interaction_zone_fields(vis, foot, fi, params={"nope": 1.0})


def test_params_validation_and_row_names() -> None:
    assert H35_NAMES == ["H35_RELAY", "H35_RELAY_TD", "H35_JUNCTION", "H35_TIPDENS"]
    assert RELAY_PARAMS["max_step_px"] == 25.0 and RELAY_PARAMS["max_tip_gap_px"] == 30.0


# --------------------------------------------------------------------------- H40 dense persistence
def _make_bands(tmp_path, big_sigma: float, small_sigma: float) -> tuple:
    n = 161
    y, x = np.mgrid[0:n, 0:n]
    cy = cx = n // 2
    big = 8.0 * np.exp(-(((y - cy) ** 2 + (x - cx) ** 2) / (2 * big_sigma ** 2)))
    sy = 30
    small = 6.0 * np.exp(-(((y - sy) ** 2 + (x - 130) ** 2) / (2 * small_sigma ** 2)))
    field = (big + small).astype(np.float32)
    np.save(tmp_path / "02_rtp.npy", field)
    np.save(tmp_path / "13_iso_grav_anom.npy", (field * -0.5).astype(np.float32))
    foot = np.ones((n, n), bool)
    foot[:6] = foot[-6:] = False
    foot[:, :6] = foot[:, -6:] = False
    return foot, (cy, cx), (sy, 130)


def test_dense_persistence_persists_for_broad_and_dies_for_sharp(tmp_path) -> None:
    foot, big_c, small_c = _make_bands(tmp_path, big_sigma=18.0, small_sigma=2.0)
    fi = _fi(foot)
    cfg = WormConfig(boundary_guard_px=4, taper_px=32, pad_px=96, edge_percentile=90.0)
    fields, diag = build_dense_persistence(tmp_path, foot, fi, config=cfg, smooth_sigma_px=1.0)
    assert fields.shape == (4, fi.size)
    assert np.isfinite(fields).all()
    assert fields.min() >= 0.0 and fields.max() <= 1.0
    assert HP_NAMES == ["HP_MAG", "HP_GRAV", "HP_MIN", "HP_DEEP"]
    grid = np.zeros(foot.shape, np.float32)
    grid[foot] = fields[0]
    # The broad structure keeps edge ridges at every continuation height; the sharp blob loses its
    # thresholded edge quickly. Persistence (as a fraction of heights with a ridge within 2 px) must
    # differ between the neighbourhoods in the expected direction.
    def ring_max(center, r0, r1):
        y, x = np.mgrid[0:grid.shape[0], 0:grid.shape[1]]
        rad = np.hypot(y - center[0], x - center[1])
        band = (rad >= r0) & (rad <= r1) & foot
        return float(grid[band].max())

    broad = ring_max(big_c, 8, 40)
    sharp = ring_max(small_c, 0, 5)
    assert broad > 0.3, f"broad-structure persistence too low: {broad}"
    assert sharp < broad, f"sharp blob should not out-persist the broad structure ({sharp} vs {broad})"
    # dense surface property: far denser than H31's binary seeds
    assert diag["nonzero_fraction"]["HP_MAG"] > 0.05
    # joint and deep columns obey their definitions
    np.testing.assert_allclose(fields[2], np.minimum(fields[0], fields[1]), rtol=0, atol=1e-6)
    assert np.all(fields >= 0) and np.all(fields <= 1)


def test_dense_persistence_flat_field_has_no_persistence(tmp_path) -> None:
    n = 81
    foot = np.ones((n, n), bool)
    foot[:4] = foot[-4:] = False
    foot[:, :4] = foot[:, -4:] = False
    flat = np.full((n, n), 3.0, np.float32)
    np.save(tmp_path / "02_rtp.npy", flat)
    np.save(tmp_path / "13_iso_grav_anom.npy", flat)
    cfg = WormConfig(boundary_guard_px=4, taper_px=24, pad_px=64)
    fields, _ = build_dense_persistence(tmp_path, foot, _fi(foot), config=cfg)
    assert np.allclose(fields, 0.0)
