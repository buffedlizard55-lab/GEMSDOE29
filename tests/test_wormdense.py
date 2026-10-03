from __future__ import annotations

import numpy as np
import pytest

from gemsdoe.wormdense import W_NAMES, WormConfig, build_branch, build_w_features


def _test_config(**overrides) -> WormConfig:
    values = dict(
        cell_size_m=100.0,
        heights_m=(0, 100, 200, 400, 800, 1200),
        taper_px=16,
        pad_px=32,
        boundary_guard_px=16,
        edge_percentile=90.0,
        max_match_px=2.0,
    )
    values.update(overrides)
    return WormConfig(**values)


def _step_grid(size: int = 160) -> tuple[np.ndarray, np.ndarray]:
    """A sharp vertical step edge at the grid centre, NaN outside an inset footprint."""
    y, x = np.mgrid[:size, :size]
    footprint = np.zeros((size, size), dtype=bool)
    footprint[16:-16, 16:-16] = True
    field = np.tanh((x - size / 2) / 2.5).astype(np.float32)
    field += (y.astype(np.float32) - size / 2) * 0.0002
    field[~footprint] = np.nan
    return field, footprint


def _gauss_grid(size: int = 160, sigma_px: float = 25.0) -> tuple[np.ndarray, np.ndarray]:
    """A broad smooth anomaly (deep-source proxy): its rim persists to high continuation."""
    y, x = np.mgrid[:size, :size]
    footprint = np.zeros((size, size), dtype=bool)
    footprint[16:-16, 16:-16] = True
    c = size / 2
    field = np.exp(-((x - c) ** 2 + (y - c) ** 2) / (2 * sigma_px**2)).astype(np.float32)
    field[~footprint] = np.nan
    return field, footprint


def test_branch_shape_finite_and_masked():
    field, foot = _step_grid()
    cols, diag = build_branch(field, foot, config=_test_config())
    assert cols.shape == (4, *foot.shape)
    assert cols.dtype == np.float32
    assert not np.isinf(cols).any()
    assert (cols[:, ~foot] == 0.0).all()
    # fully finite input -> no NaN anywhere in the footprint
    assert np.isfinite(cols[:, foot]).all()
    assert diag["per_height_thresholds"] and len(diag["per_height_thresholds"]) == 5


def test_nan_input_becomes_nan_output():
    """A-family re-masking convention: nodata in the input band is NaN in the W columns
    (HGB-native missing values), except the margin band which is exactly zero."""
    field, foot = _step_grid()
    block = np.zeros_like(foot)
    block[60:80, 60:80] = True  # 20x20 nodata block well inside the margin band
    field[foot & block] = np.nan
    cols, _ = build_branch(field, foot, config=_test_config())
    assert np.isnan(cols[:, foot & block]).all()
    assert np.isfinite(cols[:, foot & ~block]).all()


def test_margin_band_is_zero():
    """The taper-artifact margin (taper_px+4 from the boundary) must be exactly zero."""
    field, foot = _step_grid()
    cfg = _test_config()
    cols, diag = build_branch(field, foot, config=cfg)
    from scipy.ndimage import distance_transform_edt

    padded = np.pad(foot, 1, mode="constant", constant_values=False)
    d = distance_transform_edt(padded)[1:-1, 1:-1]
    margin_band = foot & (d < cfg.taper_px + 4)
    assert margin_band.sum() > 0
    assert (cols[:, margin_band] == 0.0).all()
    assert diag["margin_zero_band_px"] == cfg.taper_px + 4


def test_sharp_step_dies_young_and_is_dense():
    """A sharp surface-trace edge (1-3 px) keeps level-0 HGM but loses persistence with height:
    LAST is small; the FRAC/E0 columns are still spatially dense and peak at the edge."""
    field, foot = _step_grid()
    cols, _ = build_branch(field, foot, config=_test_config())
    frac, last, e0, deep = cols
    x = np.arange(foot.shape[1])
    edge_band = np.abs(x - foot.shape[1] / 2) < 8
    band = foot & np.broadcast_to(edge_band, foot.shape)
    assert frac[foot].mean() > 0.02  # dense, unlike H31 (<0.1%)
    assert (frac >= 0).all() and (frac <= 1).all()
    # the sharp edge is dominated by high wavenumber: most of it dies below the top rung
    assert last[band].mean() < 0.6
    # level-0 amplitude clearly peaks at the edge
    assert e0[band].mean() > 2 * e0[foot].mean()


def test_broad_anomaly_survives_higher_than_sharp_noise():
    """Continuation kills fine texture before broad structure: LAST ranks by apparent depth."""
    field, foot = _gauss_grid(sigma_px=25.0)
    cols, _ = build_branch(field, foot, config=_test_config())
    frac, last, e0, deep = cols
    # the rim of a broad anomaly must survive to the 1200 m rung somewhere in the field
    assert (last[foot] == 1.0).sum() > 0
    assert deep[foot].max() > 0.0
    # E0 should peak at the anomaly rim, not its flat centre
    y, x = np.mgrid[:160, :160]
    c = 80.0
    r = np.hypot(x - c, y - c)
    rim_band = (r > 12) & (r < 40) & foot
    centre_band = (r < 6) & foot
    assert e0[rim_band].mean() > e0[centre_band].mean()
    # the broad anomaly persists higher on average than a sharp 2.5-px step
    step_field, _ = _step_grid()
    step_last = build_branch(step_field, foot, config=_test_config())[0][1]
    assert last[foot].mean() > step_last[foot].mean()


def test_smooth_weak_field_has_low_persistence():
    """A near-flat field (plane + one weak broad bump) has little 'significant edge' mass."""
    y, x = np.mgrid[:160, :160]
    footprint = np.zeros((160, 160), dtype=bool)
    footprint[16:-16, 16:-16] = True
    field = (x * 0.001 + y * 0.0007).astype(np.float32)
    c = 80.0
    field += 0.05 * np.exp(-((x - c) ** 2 + (y - c) ** 2) / (2 * 20.0**2)).astype(np.float32)
    field[~footprint] = np.nan
    cols, _ = build_branch(field, footprint, config=_test_config())
    frac, last = cols[0], cols[1]
    assert frac[footprint].mean() < 0.30
    assert (last == 0.0).sum() > 0.5 * int(footprint.sum())


def test_w_features_full_cache():
    rtp, foot = _step_grid()
    grav, _ = _gauss_grid(sigma_px=18.0)
    feats, meta = build_w_features(None, foot, rtp, grav, config=_test_config())
    assert feats.shape == (12, int(foot.sum()))
    assert meta["names"] == W_NAMES
    assert np.isfinite(feats).all()
    # all twelve columns must be meaningfully dense (the H31 defect was <0.1% nonzero)
    for i, n in enumerate(W_NAMES):
        if "FRAC" in n or "E0" in n or "DEEP" in n:
            assert meta["column_stats"][n]["nonzero_fraction"] > 0.02, n
    # the three branches must not be identical (pseudogravity integrates, gravity is independent)
    fr = [feats[i] for i in range(len(W_NAMES)) if W_NAMES[i].endswith("FRAC")]
    assert not np.array_equal(fr[0], fr[1])
    assert not np.array_equal(fr[0], fr[2])


def test_branch_rejects_bad_footprint():
    field, foot = _step_grid()
    with pytest.raises(ValueError):
        build_branch(field, np.zeros_like(foot), config=_test_config())
