"""Synthetic unit tests for the H43 drainage-network organization fields (no competition data required)."""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe.h43 import (
    H43_NAMES,
    build_h43_fields,
    d8_order,
    degenerate_fields,
    fill_dem,
    prepare_drainage,
    repeated_median_log_fit,
    smoothed_slope,
    stream_power,
)


def test_fill_dem_plane_with_circular_pit_is_monotone_and_never_below_input():
    # Synthetic plane tilted downhill along +x (west to east): z(r, c) = 200.0 - 1.5 * c
    H, W = 50, 60
    rr, cc = np.mgrid[0:H, 0:W]
    plane = (200.0 - 1.5 * cc).astype(np.float64)
    # Carve a closed circular depression in the middle of the plane
    pit_mask = (rr - 25) ** 2 + (cc - 30) ** 2 <= 8 ** 2
    elev = plane.copy()
    elev[pit_mask] -= 25.0

    filled = fill_dem(elev)
    assert np.isfinite(filled).all()
    # Filled surface must never be below the input anywhere
    assert (filled >= elev - 1e-12).all()
    # Outside the pit, the plane was already monotone to the boundary and must be unchanged
    assert np.allclose(filled[~pit_mask], plane[~pit_mask], atol=1e-9)
    # Inside the pit below the downhill spill rim (z = 200 - 1.5*39 = 141.5), every cell is raised above its carved value
    sub_spill = pit_mask & (elev < 141.5)
    assert sub_spill.any()
    assert (filled[sub_spill] > elev[sub_spill]).all()
    assert (filled[sub_spill] >= 141.5).all()
    # Along the central row across the pit toward the downhill outlet (+x), filled elevation is non-increasing
    row_profile = filled[25, 15:50]
    assert (np.diff(row_profile) <= 1e-5).all()
    # Routing on the filled DEM leaves zero trapped interior cells and conserves mass at the boundary
    acc, _, outlets = d8_order(filled, return_basins=True)
    assert float(acc[outlets].sum()) == pytest.approx(float(H * W), rel=1e-6)


def test_d8_order_tilted_plane_grows_linearly_along_x():
    # Plane tilted downhill along +x: every interior cell (r, c) drains strictly to (r, c + 1)
    H, W = 30, 45
    _, cc = np.mgrid[0:H, 0:W]
    elev = (500.0 - 2.0 * cc).astype(np.float64)
    acc, _, outlets = d8_order(elev, return_basins=True)
    # For any interior row (1 <= r <= H - 2) and column c >= 1:
    # col 0 is a boundary outlet (drains off-grid), while col 1..W-1 accumulate along +x with slope 1 cell/col
    for r in range(1, H - 1):
        expected = np.arange(1, W, dtype=np.float64)
        assert np.allclose(acc[r, 1:], expected, atol=1e-6)
        assert np.allclose( np.diff(acc[r, 1:]), 1.0, atol=1e-6 )
    assert float(acc[outlets].sum()) == pytest.approx(float(H * W), rel=1e-6)


def test_d8_order_v_valley_peaks_on_thalweg_and_is_symmetric():
    # Symmetric V-valley draining south (+r) with thalweg at mid-column x_mid = 20
    H, W = 40, 41
    x_mid = 20
    rr, cc = np.mgrid[0:H, 0:W]
    # Make cross-valley slope steeper than down-valley slope so side walls route toward the thalweg
    elev = (400.0 - 1.0 * rr + 3.0 * np.abs(cc - x_mid)).astype(np.float64)
    filled = fill_dem(elev)
    acc, _, outlets = d8_order(filled, return_basins=True)

    # Symmetry about the thalweg column x_mid across the entire grid
    for offset in range(1, x_mid + 1):
        assert np.allclose(acc[:, x_mid - offset], acc[:, x_mid + offset], atol=1e-6)

    # In the lower half of the valley, accumulation peaks strictly on the thalweg column x_mid
    for r in range(15, H - 1):
        assert int(np.argmax(acc[r, :])) == x_mid
        assert acc[r, x_mid] > acc[r, x_mid - 1]
        assert acc[r, x_mid] > acc[r, x_mid + 1]

    # Exact mass conservation at boundary outlets
    assert float(acc[outlets].sum()) == pytest.approx(float(H * W), rel=1e-6)


def test_stream_power_and_repeated_median_fit_detect_knickpoint():
    rng = np.random.default_rng(42)
    area = np.geomspace(25.0, 50_000.0, 600)
    # Equilibrium concave profile: S = 10^0.6 * A^(-0.45)
    true_slope = (10.0 ** 0.6) * (area ** -0.45)
    # Inject a synthetic range-front knickpoint anomaly on 20 channel segments (5x steeper)
    slope = true_slope.copy()
    knick_idx = np.arange(250, 270)
    slope[knick_idx] *= 5.0
    # Add tiny background multiplicative jitter
    slope *= np.exp(rng.normal(0.0, 0.01, size=area.size))

    b1, b0 = repeated_median_log_fit(np.log10(area), np.log10(slope), n_bins=16)
    assert b1 == pytest.approx(-0.45, abs=0.03)
    assert b0 == pytest.approx(0.60, abs=0.08)

    omega = stream_power(area.reshape(20, 30), slope.reshape(20, 30), m=0.5).ravel()
    assert (omega[knick_idx] > np.median(omega)).all()


def test_prepare_drainage_and_build_h43_fields_bounds_and_leak_free():
    H, W = 80, 80
    rr, cc = np.mgrid[0:H, 0:W]
    foot = np.ones((H, W), bool)
    foot[:4, :] = False
    foot[:, :4] = False
    # Concave valley draining toward +r, with a sharp fault-scarp step at r = 45
    elev = 300.0 - 1.2 * rr + 2.5 * np.abs(cc - 42) + np.where(rr < 45, 18.0, 0.0)
    elev = elev.astype(np.float32)
    # Inject a few internal NaNs inside the footprint to exercise nearest-valid repair
    elev[20, 20] = np.nan
    elev[35, 50] = np.nan

    drainage = prepare_drainage(elev, foot)
    assert drainage.diagnostics["mass_conserved"] is True
    assert drainage.diagnostics["n_interior_trapped"] == 0
    assert drainage.diagnostics["n_elev_nan_in_footprint_filled"] == 2

    fi = np.flatnonzero(foot.ravel())
    visible = np.zeros((H, W), bool)
    visible[45, 42] = True  # place a visible catalogue fault right on the knickpoint
    scarp = np.full(fi.size, 0.6, np.float32)

    fields_vis, diag_vis = build_h43_fields(
        drainage, visible=visible, footprint=foot, footprint_idx=fi, scarp_vec=scarp
    )
    assert fields_vis.shape == (len(H43_NAMES), fi.size)
    assert fields_vis.dtype == np.float32
    assert np.isfinite(fields_vis).all()
    assert float(fields_vis.min()) >= 0.0 and float(fields_vis.max()) <= 1.0
    assert degenerate_fields(fields_vis) == []

    # When the entire footprint is marked visible, H43_OFF_FRONT (row 3) must vanish identically while
    # the draw-independent columns (0, 1, 2, 4) remain unchanged.
    fields_all_vis, diag_all = build_h43_fields(
        drainage, visible=foot, footprint=foot, footprint_idx=fi, scarp_vec=scarp
    )
    assert diag_all["off_catalogue_footprint_fraction"] == 0.0
    assert float(fields_all_vis[3].max()) == 0.0
    assert np.array_equal(fields_vis[0], fields_all_vis[0])
    assert np.array_equal(fields_vis[1], fields_all_vis[1])
    assert np.array_equal(fields_vis[2], fields_all_vis[2])
    assert np.array_equal(fields_vis[4], fields_all_vis[4])

    # Smoothed slope helper returns zero outside valid mask and finite values inside
    sl = smoothed_slope(elev, foot)
    assert (sl[~foot] == 0.0).all() and np.isfinite(sl).all()


def test_degenerate_fields_flags_sparse_columns():
    fields = np.zeros((5, 50_000), np.float32)
    fields[0, :10] = 0.8
    problems = degenerate_fields(fields)
    assert len(problems) == 5
    assert any(p.startswith("H43_LNACC") for p in problems)
    assert any(p.startswith("H43_OFF_FRONT") for p in problems)
    dense = np.full((5, 1000), 0.25, np.float32)
    assert degenerate_fields(dense) == []
